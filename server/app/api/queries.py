from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_workspace_id
from app.db.session import get_db
from app.schemas.queries import (
    QueryHistoryCitation,
    QueryHistoryDetailResponse,
    QueryHistoryItem,
    QueryHistoryListResponse,
)

router = APIRouter()
QUERY_LOG_CHAT_MARKER = "__CHAT_SESSION__"


def _build_citations(
    *,
    db: Session,
    workspace_id: uuid.UUID,
    chunk_ids: list[uuid.UUID],
) -> list[QueryHistoryCitation]:
    if not chunk_ids:
        return []

    rows = db.execute(
        text(
            """
            SELECT id AS chunk_id, page_start
            FROM chunks
            WHERE workspace_id = :workspace_id
              AND id = ANY(:chunk_ids)
            """
        ),
        {
            "workspace_id": workspace_id,
            "chunk_ids": chunk_ids,
        },
    ).mappings().all()
    by_chunk = {row["chunk_id"]: int(row["page_start"]) for row in rows}
    return [
        QueryHistoryCitation(page_number=by_chunk[chunk_id], chunk_id=chunk_id)
        for chunk_id in chunk_ids
        if chunk_id in by_chunk
    ]


@router.get("", response_model=QueryHistoryListResponse)
def list_queries(
    document_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> QueryHistoryListResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="offset must be >= 0")

    where_sql = "workspace_id = :workspace_id AND COALESCE(error_message, '') <> :chat_marker"
    params: dict[str, object] = {
        "workspace_id": workspace_id,
        "chat_marker": QUERY_LOG_CHAT_MARKER,
        "document_id": document_id,
        "limit": limit,
        "offset": offset,
    }
    if document_id is not None:
        where_sql += " AND :document_id = ANY(documents_searched)"

    total = int(
        db.execute(
            text(f"SELECT COUNT(*) FROM query_logs WHERE {where_sql}"),
            params,
        ).scalar_one()
        or 0
    )

    rows = db.execute(
        text(
            f"""
            SELECT id, query_text, answer_text, error_message, documents_searched, created_at
            FROM query_logs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    items: list[QueryHistoryItem] = []
    for row in rows:
        searched_docs = list(row["documents_searched"] or [])
        answer_text = row["answer_text"] or row["error_message"] or ""
        items.append(
            QueryHistoryItem(
                id=row["id"],
                document_id=searched_docs[0] if searched_docs else None,
                question=row["query_text"],
                created_at=row["created_at"],
                answer_preview=str(answer_text)[:200],
            )
        )

    return QueryHistoryListResponse(items=items, limit=limit, offset=offset, total=total)


@router.get("/{query_id}", response_model=QueryHistoryDetailResponse)
def get_query(
    query_id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> QueryHistoryDetailResponse:
    row = db.execute(
        text(
            """
            SELECT id, workspace_id, user_id, query_text, documents_searched, retrieved_chunk_ids,
                   chunk_scores, answer_text, error_message, retrieval_latency_ms, llm_latency_ms,
                   total_latency_ms, embedding_tokens_used, llm_input_tokens, llm_output_tokens,
                   total_tokens_used, created_at
            FROM query_logs
            WHERE id = :query_id
              AND workspace_id = :workspace_id
              AND COALESCE(error_message, '') <> :chat_marker
            LIMIT 1
            """
        ),
        {"query_id": query_id, "workspace_id": workspace_id, "chat_marker": QUERY_LOG_CHAT_MARKER},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query log not found")

    chunk_ids = list(row["retrieved_chunk_ids"] or [])
    citations = _build_citations(db=db, workspace_id=workspace_id, chunk_ids=chunk_ids)
    return QueryHistoryDetailResponse(
        id=row["id"],
        workspace_id=row["workspace_id"],
        user_id=row["user_id"],
        question=row["query_text"],
        document_ids=list(row["documents_searched"] or []),
        retrieved_chunk_ids=chunk_ids,
        chunk_scores=[float(score) for score in list(row["chunk_scores"] or [])],
        answer=row["answer_text"],
        error_message=row["error_message"],
        retrieval_latency_ms=row["retrieval_latency_ms"],
        llm_latency_ms=row["llm_latency_ms"],
        total_latency_ms=int(row["total_latency_ms"]),
        embedding_tokens_used=int(row["embedding_tokens_used"]),
        llm_input_tokens=row["llm_input_tokens"],
        llm_output_tokens=row["llm_output_tokens"],
        total_tokens_used=int(row["total_tokens_used"]),
        citations=citations,
        created_at=row["created_at"],
    )
