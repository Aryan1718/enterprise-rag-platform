from datetime import UTC, datetime
import math

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_workspace_id
from app.core.token_budget import get_budget_status
from app.db.session import get_db
from app.schemas.usage import (
    ObservabilityDocumentSummary,
    ObservabilityQuerySummary,
    ObservabilityQueryVolumePoint,
    ObservabilityRecentError,
    ObservabilityResponse,
    ObservabilityTopDocument,
    UsageTodayResponse,
)

router = APIRouter()


@router.get("/today", response_model=UsageTodayResponse)
def get_usage_today(
    workspace_id=Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> dict[str, int | datetime]:
    return get_budget_status(
        db=db,
        workspace_id=workspace_id,
        usage_date_utc=datetime.now(UTC),
    )


def _percentile(values: list[int], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(math.ceil((p / 100.0) * len(sorted_values))) - 1
    index = max(0, min(index, len(sorted_values) - 1))
    return float(sorted_values[index])


@router.get("/observability", response_model=ObservabilityResponse)
def get_observability(
    workspace_id=Depends(get_workspace_id),
    db: Session = Depends(get_db),
) -> ObservabilityResponse:
    now = datetime.now(UTC)
    usage_today = get_budget_status(
        db=db,
        workspace_id=workspace_id,
        usage_date_utc=now,
    )

    total_queries = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM query_logs
                WHERE workspace_id = :workspace_id
                """
            ),
            {"workspace_id": workspace_id},
        ).scalar_one()
        or 0
    )

    query_rows_24h = db.execute(
        text(
            """
            SELECT total_latency_ms, error_message
            FROM query_logs
            WHERE workspace_id = :workspace_id
              AND created_at >= NOW() - INTERVAL '24 hours'
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().all()
    queries_last_24h = len(query_rows_24h)
    error_count_last_24h = sum(1 for row in query_rows_24h if row["error_message"])
    latencies = [int(row["total_latency_ms"]) for row in query_rows_24h if row["total_latency_ms"] is not None]
    avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
    p95_latency = _percentile(latencies, 95.0)
    error_rate = (error_count_last_24h / queries_last_24h) if queries_last_24h else 0.0

    volume_rows = db.execute(
        text(
            """
            SELECT
                TO_CHAR((created_at AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD') AS day,
                COUNT(*) AS count,
                SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) AS errors
            FROM query_logs
            WHERE workspace_id = :workspace_id
              AND created_at >= NOW() - INTERVAL '7 days'
            GROUP BY (created_at AT TIME ZONE 'UTC')::date
            ORDER BY (created_at AT TIME ZONE 'UTC')::date ASC
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().all()
    query_volume = [
        ObservabilityQueryVolumePoint(
            date=str(row["day"]),
            count=int(row["count"] or 0),
            errors=int(row["errors"] or 0),
        )
        for row in volume_rows
    ]

    doc_status_rows = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS count
            FROM documents
            WHERE workspace_id = :workspace_id
            GROUP BY status
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().all()
    by_status = {str(row["status"]): int(row["count"] or 0) for row in doc_status_rows}
    ready_count = by_status.get("ready", 0) + by_status.get("indexed", 0)
    processing_count = (
        by_status.get("pending_upload", 0)
        + by_status.get("uploaded", 0)
        + by_status.get("queued", 0)
        + by_status.get("extracting", 0)
        + by_status.get("indexing", 0)
    )
    failed_count = by_status.get("failed", 0)
    documents = ObservabilityDocumentSummary(
        total=sum(by_status.values()),
        ready=ready_count,
        processing=processing_count,
        failed=failed_count,
    )

    top_doc_rows = db.execute(
        text(
            """
            SELECT
                d.id AS document_id,
                d.filename AS filename,
                COUNT(ql.id) AS query_count,
                SUM(CASE WHEN ql.error_message IS NOT NULL THEN 1 ELSE 0 END) AS error_count,
                MAX(ql.created_at) AS last_queried_at
            FROM documents d
            LEFT JOIN query_logs ql
              ON ql.workspace_id = d.workspace_id
             AND d.id = ql.documents_searched[1]
            WHERE d.workspace_id = :workspace_id
            GROUP BY d.id, d.filename
            ORDER BY query_count DESC, last_queried_at DESC NULLS LAST
            LIMIT 5
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().all()
    top_documents = [
        ObservabilityTopDocument(
            document_id=str(row["document_id"]),
            filename=str(row["filename"]),
            query_count=int(row["query_count"] or 0),
            error_count=int(row["error_count"] or 0),
            last_queried_at=row["last_queried_at"],
        )
        for row in top_doc_rows
    ]

    error_rows = db.execute(
        text(
            """
            SELECT id, created_at, query_text, error_message, documents_searched
            FROM query_logs
            WHERE workspace_id = :workspace_id
              AND error_message IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings().all()
    recent_errors = []
    for row in error_rows:
        docs = list(row["documents_searched"] or [])
        recent_errors.append(
            ObservabilityRecentError(
                query_id=str(row["id"]),
                created_at=row["created_at"],
                question=str(row["query_text"]),
                error_message=str(row["error_message"]),
                document_id=str(docs[0]) if docs else None,
            )
        )

    return ObservabilityResponse(
        generated_at=now,
        window_days=7,
        usage_today=UsageTodayResponse(**usage_today),
        query_summary=ObservabilityQuerySummary(
            total_queries=total_queries,
            queries_last_24h=queries_last_24h,
            error_count_last_24h=error_count_last_24h,
            error_rate_last_24h=error_rate,
            avg_latency_ms_last_24h=avg_latency,
            p95_latency_ms_last_24h=p95_latency,
        ),
        query_volume=query_volume,
        documents=documents,
        top_documents=top_documents,
        recent_errors=recent_errors,
    )
