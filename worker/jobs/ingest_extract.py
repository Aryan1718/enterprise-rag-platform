from __future__ import annotations

import logging
from pathlib import Path
import uuid

from redis import Redis
from rq import Queue
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.core.storage import download_object_bytes
from app.db.session import SessionLocal

try:
    from pypdf import PdfReader
except Exception:  # noqa: BLE001
    from PyPDF2 import PdfReader  # type: ignore[assignment]


logger = logging.getLogger(__name__)


def _set_document_status(
    *,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    status: str,
    error_message: str | None = None,
) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                UPDATE documents
                SET status = :status,
                    error_message = :error_message,
                    updated_at = NOW()
                WHERE id = :document_id
                  AND workspace_id = :workspace_id
                """
            ),
            {
                "status": status,
                "error_message": error_message,
                "document_id": document_id,
                "workspace_id": workspace_id,
            },
        )
        db.commit()


def _document_has_column(db, column_name: str) -> bool:
    result = db.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'documents'
              AND column_name = :column_name
            """
        ),
        {"column_name": column_name},
    ).scalar_one_or_none()
    return result is not None


def _allowed_document_statuses(db) -> set[str]:
    row = db.execute(
        text(
            """
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'documents'
              AND c.conname = 'chk_status'
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if not row:
        return set()
    definition = str(row)
    if "IN (" not in definition:
        return set()
    inside = definition.split("IN (", 1)[1].rsplit(")", 1)[0]
    return {part.strip().strip("'\"") for part in inside.split(",")}


def ingest_extract(workspace_id: str, document_id: str, bucket: str, storage_path: str) -> dict:
    workspace_uuid = uuid.UUID(workspace_id)
    document_uuid = uuid.UUID(document_id)
    temp_path = Path(f"/tmp/{document_uuid}.pdf")

    with SessionLocal() as db:
        allowed = _allowed_document_statuses(db)
    extracting_status = "extracting" if "extracting" in allowed else "indexing"
    _set_document_status(workspace_id=workspace_uuid, document_id=document_uuid, status=extracting_status)

    try:
        file_bytes = download_object_bytes(bucket=bucket, path=storage_path)
        temp_path.write_bytes(file_bytes)

        reader = PdfReader(str(temp_path))
        pages_total = len(reader.pages)

        with SessionLocal() as db:
            # Idempotency: reruns overwrite prior extraction for this document.
            db.execute(
                text(
                    """
                    DELETE FROM document_pages
                    WHERE workspace_id = :workspace_id
                      AND document_id = :document_id
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid},
            )

            for page_index, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                db.execute(
                    text(
                        """
                        INSERT INTO document_pages (workspace_id, document_id, page_number, content)
                        VALUES (:workspace_id, :document_id, :page_number, :content)
                        """
                    ),
                    {
                        "workspace_id": workspace_uuid,
                        "document_id": document_uuid,
                        "page_number": page_index + 1,
                        "content": page_text,
                    },
                )

            update_fields = ["page_count = :page_count", "status = 'indexing'", "error_message = NULL", "updated_at = NOW()"]
            params: dict[str, object] = {
                "workspace_id": workspace_uuid,
                "document_id": document_uuid,
                "page_count": pages_total,
            }
            if _document_has_column(db, "pages_total"):
                update_fields.append("pages_total = :pages_total")
                params["pages_total"] = pages_total

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
            db.commit()

        redis_conn = Redis.from_url(settings.REDIS_URL)
        queue = Queue("ingest_index", connection=redis_conn)
        queue.enqueue(
            "jobs.ingest_index.ingest_index",
            workspace_id=workspace_id,
            document_id=document_id,
        )

        return {
            "document_id": document_id,
            "pages_total": pages_total,
            "status": "indexing",
        }
    except IntegrityError as exc:
        logger.exception(
            "ingest_extract status transition failed due to DB constraint",
            extra={"workspace_id": workspace_id, "document_id": document_id},
        )
        _set_document_status(
            workspace_id=workspace_uuid,
            document_id=document_uuid,
            status="failed",
            error_message=f"Status constraint mismatch: {exc.orig}",
        )
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "ingest_extract failed",
            extra={"workspace_id": workspace_id, "document_id": document_id},
        )
        _set_document_status(
            workspace_id=workspace_uuid,
            document_id=document_uuid,
            status="failed",
            error_message=str(exc)[:2000],
        )
        raise
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
