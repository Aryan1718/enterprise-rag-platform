from __future__ import annotations

import hashlib
import logging
import math
import uuid

from openai import OpenAI
from sqlalchemy import text

from app.config import settings, utc_today
from app.core.errors import BudgetExceededError
from app.core.token_budget import commit_usage, release_tokens, reserve_tokens
from app.db.session import SessionLocal

try:
    import tiktoken
except Exception:  # noqa: BLE001
    tiktoken = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
CHUNK_SIZE_TOKENS = 500
OVERLAP_TOKENS = 100


def _set_document_failed(workspace_id: uuid.UUID, document_id: uuid.UUID, error_message: str) -> None:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                UPDATE documents
                SET status = 'failed',
                    error_message = :error_message,
                    updated_at = NOW()
                WHERE id = :document_id
                  AND workspace_id = :workspace_id
                """
            ),
            {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "error_message": error_message[:2000],
            },
        )
        db.commit()


def _estimate_embedding_tokens(text_value: str) -> int:
    return max(1, int(math.ceil((len(text_value) / 4.0) * 1.1)))


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


def _get_encoding():
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # noqa: BLE001
        return None


def chunk_text(text_value: str, chunk_size_tokens: int = CHUNK_SIZE_TOKENS, overlap_tokens: int = OVERLAP_TOKENS) -> list[str]:
    normalized = (text_value or "").strip()
    if not normalized:
        return []

    encoding = _get_encoding()
    if encoding is None:
        # Fallback approximation aligned to 4 chars/token if tokenizer is unavailable.
        chunk_size_chars = max(1, chunk_size_tokens * 4)
        overlap_chars = max(0, overlap_tokens * 4)
        chunks: list[str] = []
        start = 0
        text_len = len(normalized)
        while start < text_len:
            end = min(text_len, start + chunk_size_chars)
            piece = normalized[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= text_len:
                break
            start = max(0, end - overlap_chars)
        return chunks

    token_ids = encoding.encode(normalized)
    if not token_ids:
        return []

    chunks: list[str] = []
    start = 0
    total = len(token_ids)
    while start < total:
        end = min(total, start + chunk_size_tokens)
        piece = encoding.decode(token_ids[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end >= total:
            break
        start = max(0, end - overlap_tokens)
    return chunks


def _embedding_to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.10f}" for value in embedding) + "]"


def ingest_index(workspace_id: str, document_id: str) -> dict:
    workspace_uuid = uuid.UUID(workspace_id)
    document_uuid = uuid.UUID(document_id)
    usage_date = utc_today()
    outstanding_reservations: list[int] = []

    try:
        with SessionLocal() as db:
            allowed_statuses = _allowed_document_statuses(db)
            document_row = db.execute(
                text(
                    """
                    SELECT id, status
                    FROM documents
                    WHERE id = :document_id
                      AND workspace_id = :workspace_id
                    LIMIT 1
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid},
            ).mappings().first()

            if document_row is None:
                raise ValueError("Document not found for workspace")
            accepted_current_statuses = {"indexing", "uploaded"}
            if "extracting" in allowed_statuses:
                accepted_current_statuses.add("extracting")
            if document_row["status"] not in accepted_current_statuses:
                raise ValueError(f"Document status must be indexing or uploaded (got: {document_row['status']})")

            db.execute(
                text(
                    """
                    UPDATE documents
                    SET status = 'indexing',
                        error_message = NULL,
                        updated_at = NOW()
                    WHERE id = :document_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid},
            )

            pages = db.execute(
                text(
                    """
                    SELECT page_number, content
                    FROM document_pages
                    WHERE workspace_id = :workspace_id
                      AND document_id = :document_id
                    ORDER BY page_number ASC
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid},
            ).mappings().all()

            db.execute(
                text(
                    """
                    DELETE FROM chunk_embeddings
                    WHERE workspace_id = :workspace_id
                      AND document_id = :document_id
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid},
            )
            db.execute(
                text(
                    """
                    DELETE FROM chunks
                    WHERE workspace_id = :workspace_id
                      AND document_id = :document_id
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid},
            )
            db.commit()

        chunk_rows: list[dict[str, object]] = []
        chunk_index = 0
        for page in pages:
            page_number = int(page["page_number"])
            for piece in chunk_text(str(page["content"] or "")):
                chunk_id = uuid.uuid4()
                chunk_rows.append(
                    {
                        "id": chunk_id,
                        "workspace_id": workspace_uuid,
                        "document_id": document_uuid,
                        "page_start": page_number,
                        "page_end": page_number,
                        "chunk_index": chunk_index,
                        "content": piece,
                        "content_hash": hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                        "token_count": _estimate_embedding_tokens(piece),
                    }
                )
                chunk_index += 1

        with SessionLocal() as db:
            for row in chunk_rows:
                db.execute(
                    text(
                        """
                        INSERT INTO chunks (
                            id, workspace_id, document_id, page_start, page_end,
                            chunk_index, content, content_hash, token_count
                        )
                        VALUES (
                            :id, :workspace_id, :document_id, :page_start, :page_end,
                            :chunk_index, :content, :content_hash, :token_count
                        )
                        """
                    ),
                    row,
                )
            db.commit()

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        model = settings.EMBEDDING_MODEL
        embedding_count = 0
        total_embedding_tokens = 0

        for row in chunk_rows:
            chunk_text_value = str(row["content"])
            estimated_tokens = _estimate_embedding_tokens(chunk_text_value)

            with SessionLocal() as db:
                reserve_tokens(
                    db=db,
                    workspace_id=workspace_uuid,
                    amount=estimated_tokens,
                    usage_date_utc=usage_date,
                    reservation_ttl_seconds=settings.RESERVATION_TTL_SECONDS,
                )
                db.commit()
            outstanding_reservations.append(estimated_tokens)

            response = client.embeddings.create(model=model, input=chunk_text_value)
            embedding = list(response.data[0].embedding)
            vector_literal = _embedding_to_vector_literal(embedding)

            with SessionLocal() as db:
                db.execute(
                    text(
                        """
                        INSERT INTO chunk_embeddings (chunk_id, workspace_id, document_id, embedding, embedding_model)
                        VALUES (:chunk_id, :workspace_id, :document_id, CAST(:embedding AS vector), :embedding_model)
                        """
                    ),
                    {
                        "chunk_id": row["id"],
                        "workspace_id": workspace_uuid,
                        "document_id": document_uuid,
                        "embedding": vector_literal,
                        "embedding_model": model,
                    },
                )
                commit_usage(
                    db=db,
                    workspace_id=workspace_uuid,
                    amount=estimated_tokens,
                    usage_date_utc=usage_date,
                )
                db.commit()
            outstanding_reservations.pop()

            embedding_count += 1
            total_embedding_tokens += estimated_tokens

        with SessionLocal() as db:
            final_status = "indexed" if "indexed" in _allowed_document_statuses(db) else "ready"
            db.execute(
                text(
                    """
                    UPDATE documents
                    SET status = :final_status,
                        error_message = NULL,
                        updated_at = NOW()
                    WHERE id = :document_id
                      AND workspace_id = :workspace_id
                    """
                ),
                {"workspace_id": workspace_uuid, "document_id": document_uuid, "final_status": final_status},
            )
            db.commit()

        return {
            "document_id": document_id,
            "status": final_status,
            "chunks_total": len(chunk_rows),
            "embeddings_total": embedding_count,
            "embedding_tokens_used": total_embedding_tokens,
        }
    except BudgetExceededError:
        for reserved in reversed(outstanding_reservations):
            try:
                with SessionLocal() as db:
                    release_tokens(
                        db=db,
                        workspace_id=workspace_uuid,
                        amount=reserved,
                        usage_date_utc=usage_date,
                    )
                    db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to release reserved tokens", extra={"document_id": document_id})
        _set_document_failed(workspace_uuid, document_uuid, "Insufficient token budget for embeddings")
        raise
    except Exception as exc:  # noqa: BLE001
        for reserved in reversed(outstanding_reservations):
            try:
                with SessionLocal() as db:
                    release_tokens(
                        db=db,
                        workspace_id=workspace_uuid,
                        amount=reserved,
                        usage_date_utc=usage_date,
                    )
                    db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to release reserved tokens", extra={"document_id": document_id})

        logger.exception(
            "ingest_index failed",
            extra={"workspace_id": workspace_id, "document_id": document_id},
        )
        _set_document_failed(workspace_uuid, document_uuid, str(exc))
        raise
