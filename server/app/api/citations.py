from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_workspace_id
from app.db.session import get_db
from app.schemas.citations import CitationSourceResponse
from app.utils.rate_limit import QUERY_RATE_LIMIT, enforce_workspace_rate_limit

router = APIRouter()


def _trim_text(value: str | None, max_chars: int) -> str | None:
    if value is None or len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return f"{value[: max_chars - 3].rstrip()}..."


@router.get("/{chunk_id}", response_model=CitationSourceResponse)
def get_citation_source(
    chunk_id: uuid.UUID,
    max_chars: int = Query(default=5000, ge=1, le=20000),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> CitationSourceResponse:
    enforce_workspace_rate_limit(
        workspace_id=workspace_id,
        operation="query",
        limit=QUERY_RATE_LIMIT,
    )

    chunk_row = db.execute(
        text(
            """
            SELECT id AS chunk_id, document_id, page_start AS page_number, content
            FROM chunks
            WHERE id = :chunk_id
              AND workspace_id = :workspace_id
            LIMIT 1
            """
        ),
        {"chunk_id": chunk_id, "workspace_id": workspace_id},
    ).mappings().first()
    if chunk_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation source not found")

    page_row = db.execute(
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
            "document_id": chunk_row["document_id"],
            "page_number": int(chunk_row["page_number"]),
        },
    ).mappings().first()

    return CitationSourceResponse(
        chunk_id=chunk_row["chunk_id"],
        document_id=chunk_row["document_id"],
        page_number=int(chunk_row["page_number"]),
        chunk_text=chunk_row["content"],
        page_text=_trim_text(page_row["content"], max_chars) if page_row is not None else None,
        highlights=[],
    )
