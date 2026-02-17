from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis import Redis
from rq import Queue
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_workspace_id
from app.config import settings
from app.core.storage import delete_object, generate_signed_upload_url, object_exists
from app.db.models import Document
from app.db.session import get_db
from app.schemas.citations import DocumentPageSourceResponse
from app.schemas.documents import (
    DocumentJobResponse,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentProgress,
    UploadCompleteRequest,
    UploadCompleteResponse,
    UploadPrepareRequest,
    UploadPrepareResponse,
)
from app.utils.rate_limit import QUERY_RATE_LIMIT, UPLOAD_COMPLETE_RATE_LIMIT, UPLOAD_PREPARE_RATE_LIMIT, enforce_workspace_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)
ALLOWED_STATUS_FILTERS = {
    "pending_upload",
    "uploading",
    "uploaded",
    "extracting",
    "indexing",
    "indexed",
    "ready",
    "failed",
}


def _idempotency_hash(payload_key: str) -> str:
    # Prefix keeps idempotency markers distinct from real file hashes.
    return f"idemp:{payload_key}"


def _find_existing_prepare_by_idempotency(
    *,
    db: Session,
    workspace_id: uuid.UUID,
    idempotency_hash: str,
) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, filename, storage_path, status
            FROM documents
            WHERE workspace_id = :workspace_id
              AND file_hash_sha256 = :idempotency_hash
            LIMIT 1
            """
        ),
        {"workspace_id": workspace_id, "idempotency_hash": idempotency_hash},
    ).mappings().first()
    if row is None:
        return None
    return {
        "id": row["id"],
        "filename": row["filename"],
        "storage_path": row["storage_path"],
        "status": row["status"],
    }


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if not sanitized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    return sanitized


def _document_columns(db: Session) -> set[str]:
    bind = db.get_bind()
    return {col["name"] for col in inspect(bind).get_columns("documents")}


def _count_for_document(db: Session, sql: str, workspace_id: uuid.UUID, document_id: uuid.UUID) -> int:
    value = db.execute(
        text(sql),
        {
            "workspace_id": workspace_id,
            "document_id": document_id,
        },
    ).scalar_one()
    return int(value or 0)


def _trim_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return f"{value[: max_chars - 3].rstrip()}..."


def _enqueue_extract(*, workspace_id: uuid.UUID, document_id: uuid.UUID, bucket: str, storage_path: str):
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue("ingest_extract", connection=redis_conn)
    return queue.enqueue(
        "jobs.ingest_extract.ingest_extract",
        workspace_id=str(workspace_id),
        document_id=str(document_id),
        bucket=bucket,
        storage_path=storage_path,
    )


def _enqueue_index(*, workspace_id: uuid.UUID, document_id: uuid.UUID):
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue("ingest_index", connection=redis_conn)
    return queue.enqueue(
        "jobs.ingest_index.ingest_index",
        workspace_id=str(workspace_id),
        document_id=str(document_id),
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="offset must be >= 0")

    if status_filter is not None and status_filter not in ALLOWED_STATUS_FILTERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Allowed: {sorted(ALLOWED_STATUS_FILTERS)}",
        )

    columns = _document_columns(db)
    has_content_type = "content_type" in columns

    where_clauses = ["workspace_id = :workspace_id"]
    params: dict[str, object] = {"workspace_id": workspace_id, "limit": limit, "offset": offset}
    if status_filter is not None:
        where_clauses.append("status = :status")
        params["status"] = status_filter
    where_sql = " AND ".join(where_clauses)

    total_sql = text(f"SELECT COUNT(*) FROM documents WHERE {where_sql}")
    total = int(db.execute(total_sql, params).scalar_one() or 0)

    content_type_select = "content_type" if has_content_type else "'application/pdf' AS content_type"
    list_sql = text(
        f"""
        SELECT id, filename, {content_type_select}, file_size_bytes, status, created_at, updated_at
        FROM documents
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
    )
    rows = db.execute(list_sql, params).mappings().all()

    items = [
        DocumentListItem(
            id=row["id"],
            filename=row["filename"],
            content_type=row["content_type"],
            file_size_bytes=int(row["file_size_bytes"]),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

    return DocumentListResponse(items=items, limit=limit, offset=offset, total=total)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    columns = _document_columns(db)
    select_fields = [
        "id",
        "filename",
        "file_size_bytes",
        "status",
        "storage_path",
        "created_at",
        "updated_at",
    ]
    if "content_type" in columns:
        select_fields.append("content_type")
    else:
        select_fields.append("'application/pdf' AS content_type")
    if "storage_bucket" in columns:
        select_fields.append("storage_bucket")
    else:
        select_fields.append("NULL AS storage_bucket")
    if "pages_total" in columns:
        select_fields.append("pages_total")
    else:
        select_fields.append("NULL AS pages_total")

    detail_sql = text(
        f"""
        SELECT {", ".join(select_fields)}
        FROM documents
        WHERE id = :document_id
          AND workspace_id = :workspace_id
        LIMIT 1
        """
    )
    row = db.execute(
        detail_sql,
        {"document_id": document_id, "workspace_id": workspace_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pages_total = row["pages_total"]
    if pages_total is None:
        pages_total = _count_for_document(
            db,
            "SELECT COUNT(*) FROM document_pages WHERE workspace_id = :workspace_id AND document_id = :document_id",
            workspace_id,
            document_id,
        )
    else:
        pages_total = int(pages_total)

    pages_extracted_count = _count_for_document(
        db,
        """
        SELECT COUNT(*)
        FROM document_pages
        WHERE workspace_id = :workspace_id
          AND document_id = :document_id
          AND NULLIF(BTRIM(content), '') IS NOT NULL
        """,
        workspace_id,
        document_id,
    )
    chunks_count = _count_for_document(
        db,
        "SELECT COUNT(*) FROM chunks WHERE workspace_id = :workspace_id AND document_id = :document_id",
        workspace_id,
        document_id,
    )
    embeddings_count = _count_for_document(
        db,
        "SELECT COUNT(*) FROM chunk_embeddings WHERE workspace_id = :workspace_id AND document_id = :document_id",
        workspace_id,
        document_id,
    )

    return DocumentDetailResponse(
        id=row["id"],
        filename=row["filename"],
        content_type=row["content_type"],
        file_size_bytes=int(row["file_size_bytes"]),
        status=row["status"],
        bucket=row["storage_bucket"] or settings.SUPABASE_STORAGE_BUCKET,
        storage_path=row["storage_path"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        progress=DocumentProgress(
            pages_total=pages_total,
            pages_extracted_count=pages_extracted_count,
            chunks_count=chunks_count,
            embeddings_count=embeddings_count,
        ),
    )


@router.get("/{document_id}/pages/{page_number}", response_model=DocumentPageSourceResponse)
def get_document_page(
    document_id: uuid.UUID,
    page_number: int,
    max_chars: int = Query(default=5000, ge=1, le=20000),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> DocumentPageSourceResponse:
    if page_number < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_number must be >= 1")

    enforce_workspace_rate_limit(
        workspace_id=workspace_id,
        operation="query",
        limit=QUERY_RATE_LIMIT,
    )

    row = db.execute(
        text(
            """
            SELECT content
            FROM document_pages
            WHERE workspace_id = :workspace_id
              AND document_id = :document_id
              AND page_number = :page_number
            LIMIT 1
            """
        ),
        {
            "workspace_id": workspace_id,
            "document_id": document_id,
            "page_number": page_number,
        },
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    return DocumentPageSourceResponse(
        document_id=document_id,
        page_number=page_number,
        text=_trim_text(str(row["content"]), max_chars),
    )


@router.post("/upload-prepare", response_model=UploadPrepareResponse, status_code=status.HTTP_201_CREATED)
def upload_prepare(
    payload: UploadPrepareRequest,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> UploadPrepareResponse:
    enforce_workspace_rate_limit(
        workspace_id=workspace_id,
        operation="documents_upload_prepare",
        limit=UPLOAD_PREPARE_RATE_LIMIT,
    )

    if payload.file_size_bytes > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds limit ({settings.MAX_FILE_SIZE_BYTES} bytes)",
        )

    allowed_content_types = {content_type.lower() for content_type in settings.ALLOWED_CONTENT_TYPES}
    if payload.content_type.lower() not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content_type. Allowed: {sorted(allowed_content_types)}",
        )

    count_stmt = select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
    document_count = int(db.execute(count_stmt).scalar_one() or 0)
    if document_count >= settings.MAX_DOCUMENTS_PER_WORKSPACE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workspace document limit reached",
        )

    now = datetime.now(UTC)
    bucket = settings.SUPABASE_STORAGE_BUCKET
    sanitized_filename = _sanitize_filename(payload.filename)
    columns = _document_columns(db)
    idempotency_hash: str | None = None

    if payload.idempotency_key and "file_hash_sha256" in columns:
        idempotency_hash = _idempotency_hash(payload.idempotency_key)
        existing = _find_existing_prepare_by_idempotency(
            db=db,
            workspace_id=workspace_id,
            idempotency_hash=idempotency_hash,
        )
        if existing is not None:
            existing_status = str(existing["status"])
            if existing_status not in {"pending_upload", "uploading"}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Upload already prepared for this key (current status: {existing_status})",
                )
            upload_url = generate_signed_upload_url(
                bucket=bucket,
                path=str(existing["storage_path"]),
                expires=settings.UPLOAD_URL_EXPIRES_SECONDS,
            )
            return UploadPrepareResponse(
                document_id=existing["id"],
                bucket=bucket,
                storage_path=str(existing["storage_path"]),
                upload_url=upload_url,
                expires_in=settings.UPLOAD_URL_EXPIRES_SECONDS,
            )

    document_id = uuid.uuid4()
    storage_path = f"{workspace_id}/{document_id}/{sanitized_filename}"
    try:
        upload_url = generate_signed_upload_url(
            bucket=bucket,
            path=storage_path,
            expires=settings.UPLOAD_URL_EXPIRES_SECONDS,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    insert_fields: dict[str, object] = {
        "id": document_id,
        "workspace_id": workspace_id,
        "filename": sanitized_filename,
        "file_size_bytes": payload.file_size_bytes,
        "storage_path": storage_path,
        "status": "pending_upload",
        "created_at": now,
        "updated_at": now,
    }
    if "content_type" in columns:
        insert_fields["content_type"] = payload.content_type
    if "storage_bucket" in columns:
        insert_fields["storage_bucket"] = bucket
    if "file_hash_sha256" in columns:
        insert_fields["file_hash_sha256"] = idempotency_hash or f"uploading:{document_id}"

    keys = list(insert_fields.keys())
    columns_sql = ", ".join(keys)
    values_sql = ", ".join(f":{key}" for key in keys)
    insert_sql = text(f"INSERT INTO documents ({columns_sql}) VALUES ({values_sql})")

    try:
        db.execute(insert_sql, insert_fields)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        # If idempotency insert raced with another request, return existing row.
        if idempotency_hash:
            existing = _find_existing_prepare_by_idempotency(
                db=db,
                workspace_id=workspace_id,
                idempotency_hash=idempotency_hash,
            )
            if existing is not None and str(existing["status"]) in {"pending_upload", "uploading"}:
                upload_url = generate_signed_upload_url(
                    bucket=bucket,
                    path=str(existing["storage_path"]),
                    expires=settings.UPLOAD_URL_EXPIRES_SECONDS,
                )
                return UploadPrepareResponse(
                    document_id=existing["id"],
                    bucket=bucket,
                    storage_path=str(existing["storage_path"]),
                    upload_url=upload_url,
                    expires_in=settings.UPLOAD_URL_EXPIRES_SECONDS,
                )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create upload placeholder: {exc}",
        ) from exc

    return UploadPrepareResponse(
        document_id=document_id,
        bucket=bucket,
        storage_path=storage_path,
        upload_url=upload_url,
        expires_in=settings.UPLOAD_URL_EXPIRES_SECONDS,
    )


@router.post("/upload-complete", response_model=UploadCompleteResponse)
def upload_complete(
    payload: UploadCompleteRequest,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> UploadCompleteResponse:
    enforce_workspace_rate_limit(
        workspace_id=workspace_id,
        operation="documents_upload_complete",
        limit=UPLOAD_COMPLETE_RATE_LIMIT,
    )

    columns = _document_columns(db)
    select_fields = ["id", "status", "storage_path"]
    if "storage_bucket" in columns:
        select_fields.append("storage_bucket")
    else:
        select_fields.append("NULL AS storage_bucket")

    select_sql = text(
        f"""
        SELECT {", ".join(select_fields)}
        FROM documents
        WHERE id = :document_id
          AND workspace_id = :workspace_id
        LIMIT 1
        """
    )
    row = db.execute(
        select_sql,
        {"document_id": payload.document_id, "workspace_id": workspace_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    stored_bucket = row["storage_bucket"] or settings.SUPABASE_STORAGE_BUCKET
    if payload.bucket != stored_bucket or payload.storage_path != row["storage_path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bucket/path mismatch for document",
        )

    if row["status"] not in {"uploading", "pending_upload"}:
        if row["status"] == "uploaded":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Upload already completed",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not in uploading state (current: {row['status']})",
        )

    exists = object_exists(bucket=payload.bucket, path=payload.storage_path)
    if exists is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded object not found in storage",
        )

    update_sql = text(
        """
        UPDATE documents
        SET status = 'uploaded',
            updated_at = :updated_at
        WHERE id = :document_id
          AND workspace_id = :workspace_id
          AND status IN ('uploading', 'pending_upload')
        """
    )
    update_result = db.execute(
        update_sql,
        {
            "updated_at": datetime.now(UTC),
            "document_id": payload.document_id,
            "workspace_id": workspace_id,
        },
    )
    if update_result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload completion conflict",
        )

    try:
        job = _enqueue_extract(
            workspace_id=workspace_id,
            document_id=payload.document_id,
            bucket=payload.bucket,
            storage_path=payload.storage_path,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue ingestion job: {exc}",
        ) from exc

    db.commit()

    return UploadCompleteResponse(
        document_id=payload.document_id,
        status="uploaded",
        job_id=job.id,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> Response:
    columns = _document_columns(db)
    storage_bucket_select = "storage_bucket" if "storage_bucket" in columns else "NULL::text AS storage_bucket"
    delete_sql = text(
        f"""
        DELETE FROM documents
        WHERE id = :document_id
          AND workspace_id = :workspace_id
        RETURNING storage_path, {storage_bucket_select}
        """
    )
    try:
        doc_row = db.execute(
            delete_sql,
            {"workspace_id": workspace_id, "document_id": document_id},
        ).mappings().first()
        if doc_row is None:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Document delete failed",
            extra={"workspace_id": str(workspace_id), "document_id": str(document_id)},
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {exc}",
        ) from exc

    bucket = doc_row["storage_bucket"] or settings.SUPABASE_STORAGE_BUCKET
    storage_path = doc_row["storage_path"]
    try:
        delete_object(bucket=bucket, path=storage_path)
    except Exception:  # noqa: BLE001
        # Keep API success after DB delete; storage cleanup can be retried asynchronously.
        logger.exception(
            "Storage delete failed after document metadata delete",
            extra={
                "workspace_id": str(workspace_id),
                "document_id": str(document_id),
                "bucket": str(bucket),
                "storage_path": str(storage_path),
            },
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/retry", response_model=DocumentJobResponse)
def retry_document(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> DocumentJobResponse:
    enforce_workspace_rate_limit(
        workspace_id=workspace_id,
        operation="documents_upload_complete",
        limit=UPLOAD_COMPLETE_RATE_LIMIT,
    )

    columns = _document_columns(db)
    select_fields = ["id", "status", "storage_path"]
    if "storage_bucket" in columns:
        select_fields.append("storage_bucket")
    else:
        select_fields.append("NULL AS storage_bucket")

    row = db.execute(
        text(
            f"""
            SELECT {", ".join(select_fields)}
            FROM documents
            WHERE id = :document_id
              AND workspace_id = :workspace_id
            LIMIT 1
            """
        ),
        {"document_id": document_id, "workspace_id": workspace_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if row["status"] != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retry is only allowed for failed documents",
        )

    update_fields = ["status = 'uploaded'", "updated_at = :updated_at"]
    params: dict[str, object] = {
        "updated_at": datetime.now(UTC),
        "document_id": document_id,
        "workspace_id": workspace_id,
    }
    if "error_message" in columns:
        update_fields.append("error_message = NULL")

    db.execute(
        text(
            f"""
            UPDATE documents
            SET {", ".join(update_fields)}
            WHERE id = :document_id
              AND workspace_id = :workspace_id
            """
        ),
        params,
    )

    try:
        job = _enqueue_extract(
            workspace_id=workspace_id,
            document_id=document_id,
            bucket=row["storage_bucket"] or settings.SUPABASE_STORAGE_BUCKET,
            storage_path=row["storage_path"],
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue retry job: {exc}",
        ) from exc

    db.commit()
    return DocumentJobResponse(document_id=document_id, status="uploaded", job_id=job.id)


@router.post("/{document_id}/reindex", response_model=DocumentJobResponse)
def reindex_document(
    document_id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> DocumentJobResponse:
    enforce_workspace_rate_limit(
        workspace_id=workspace_id,
        operation="documents_upload_complete",
        limit=UPLOAD_COMPLETE_RATE_LIMIT,
    )

    columns = _document_columns(db)
    select_fields = ["id", "status", "storage_path"]
    if "storage_bucket" in columns:
        select_fields.append("storage_bucket")
    else:
        select_fields.append("NULL AS storage_bucket")

    row = db.execute(
        text(
            f"""
            SELECT {", ".join(select_fields)}
            FROM documents
            WHERE id = :document_id
              AND workspace_id = :workspace_id
            LIMIT 1
            """
        ),
        {"document_id": document_id, "workspace_id": workspace_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if row["status"] not in {"ready", "indexed", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reindex is only allowed for ready/indexed/failed documents",
        )

    pages_count = _count_for_document(
        db,
        "SELECT COUNT(*) FROM document_pages WHERE workspace_id = :workspace_id AND document_id = :document_id",
        workspace_id,
        document_id,
    )
    has_pages = pages_count > 0
    next_status = "indexing" if has_pages else "uploaded"

    db.execute(
        text(
            """
            DELETE FROM chunk_embeddings
            WHERE workspace_id = :workspace_id
              AND document_id = :document_id
            """
        ),
        {"workspace_id": workspace_id, "document_id": document_id},
    )
    db.execute(
        text(
            """
            DELETE FROM chunks
            WHERE workspace_id = :workspace_id
              AND document_id = :document_id
            """
        ),
        {"workspace_id": workspace_id, "document_id": document_id},
    )

    update_fields = ["status = :status", "updated_at = :updated_at"]
    params = {
        "status": next_status,
        "updated_at": datetime.now(UTC),
        "document_id": document_id,
        "workspace_id": workspace_id,
    }
    if "error_message" in columns:
        update_fields.append("error_message = NULL")

    db.execute(
        text(
            f"""
            UPDATE documents
            SET {", ".join(update_fields)}
            WHERE id = :document_id
              AND workspace_id = :workspace_id
            """
        ),
        params,
    )

    try:
        if has_pages:
            job = _enqueue_index(workspace_id=workspace_id, document_id=document_id)
        else:
            job = _enqueue_extract(
                workspace_id=workspace_id,
                document_id=document_id,
                bucket=row["storage_bucket"] or settings.SUPABASE_STORAGE_BUCKET,
                storage_path=row["storage_path"],
            )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        try:
            db.execute(
                text(
                    """
                    UPDATE documents
                    SET status = 'failed',
                        error_message = :error_message,
                        updated_at = :updated_at
                    WHERE id = :document_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {
                    "error_message": str(exc)[:2000],
                    "updated_at": datetime.now(UTC),
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                },
            )
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue reindex job: {exc}",
        ) from exc

    db.commit()
    return DocumentJobResponse(document_id=document_id, status=next_status, job_id=job.id)
