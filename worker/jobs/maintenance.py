from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def cleanup_stale_reservations() -> int:
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/enterprise_rag")
    reservation_ttl_seconds = int(os.getenv("RESERVATION_TTL_SECONDS", "600"))
    if reservation_ttl_seconds < 0:
        reservation_ttl_seconds = 0

    engine = create_engine(database_url, pool_pre_ping=True)
    dialect = engine.dialect.name

    with engine.begin() as conn:
        if dialect == "postgresql":
            stmt = text(
                """
                UPDATE workspace_daily_usage
                SET tokens_reserved = 0,
                    updated_at = NOW()
                WHERE tokens_reserved > 0
                  AND updated_at < NOW() - make_interval(secs => :ttl_seconds)
                """
            )
        elif dialect == "sqlite":
            stmt = text(
                """
                UPDATE workspace_daily_usage
                SET tokens_reserved = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tokens_reserved > 0
                  AND updated_at < datetime('now', '-' || :ttl_seconds || ' seconds')
                """
            )
        else:
            # Generic fallback for dialects that support ANSI interval-like arithmetic.
            stmt = text(
                """
                UPDATE workspace_daily_usage
                SET tokens_reserved = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tokens_reserved > 0
                """
            )

        result = conn.execute(stmt, {"ttl_seconds": reservation_ttl_seconds})
        return int(result.rowcount or 0)
