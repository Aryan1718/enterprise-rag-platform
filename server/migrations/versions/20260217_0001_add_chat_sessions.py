"""add chat_sessions table

Revision ID: 20260217_0001
Revises: 
Create Date: 2026-02-17 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260217_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            document_id UUID NULL REFERENCES documents(id) ON DELETE SET NULL,
            title TEXT NOT NULL DEFAULT '',
            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_updated
            ON chat_sessions(workspace_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_document
            ON chat_sessions(workspace_id, document_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_sessions")
