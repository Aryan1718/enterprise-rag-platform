from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class QueryHistoryCitation(BaseModel):
    page_number: int
    chunk_id: uuid.UUID


class QueryHistoryItem(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID | None = None
    question: str
    created_at: datetime
    answer_preview: str
    citations: list[QueryHistoryCitation] | None = None


class QueryHistoryListResponse(BaseModel):
    items: list[QueryHistoryItem]
    limit: int
    offset: int
    total: int


class QueryHistoryDetailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    question: str
    document_ids: list[uuid.UUID]
    retrieved_chunk_ids: list[uuid.UUID]
    chunk_scores: list[float]
    answer: str | None
    error_message: str | None
    retrieval_latency_ms: int | None
    llm_latency_ms: int | None
    total_latency_ms: int
    embedding_tokens_used: int
    llm_input_tokens: int | None
    llm_output_tokens: int | None
    total_tokens_used: int
    citations: list[QueryHistoryCitation]
    created_at: datetime
