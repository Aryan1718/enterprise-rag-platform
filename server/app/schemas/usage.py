from datetime import datetime

from pydantic import BaseModel


class UsageTodayResponse(BaseModel):
    used: int
    reserved: int
    limit: int
    remaining: int
    resets_at: datetime


class ObservabilityQuerySummary(BaseModel):
    total_queries: int
    queries_last_24h: int
    error_count_last_24h: int
    error_rate_last_24h: float
    avg_latency_ms_last_24h: float
    p95_latency_ms_last_24h: float


class ObservabilityQueryVolumePoint(BaseModel):
    date: str
    count: int
    errors: int


class ObservabilityDocumentSummary(BaseModel):
    total: int
    ready: int
    processing: int
    failed: int


class ObservabilityTopDocument(BaseModel):
    document_id: str
    filename: str
    query_count: int
    error_count: int
    last_queried_at: datetime | None


class ObservabilityRecentError(BaseModel):
    query_id: str
    created_at: datetime
    question: str
    error_message: str
    document_id: str | None


class ObservabilityResponse(BaseModel):
    generated_at: datetime
    window_days: int
    usage_today: UsageTodayResponse
    query_summary: ObservabilityQuerySummary
    query_volume: list[ObservabilityQueryVolumePoint]
    documents: ObservabilityDocumentSummary
    top_documents: list[ObservabilityTopDocument]
    recent_errors: list[ObservabilityRecentError]
