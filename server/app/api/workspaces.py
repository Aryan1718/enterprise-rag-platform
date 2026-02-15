from datetime import date, datetime, time, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.core.auth import AuthenticatedUser
from app.db.models import Document, Workspace, WorkspaceDailyUsage
from app.db.session import get_db
from app.schemas.workspace import UsageTodayResponse, WorkspaceCreateRequest, WorkspaceMeResponse, WorkspaceResponse

router = APIRouter()


def _utc_resets_at(now_utc: datetime) -> datetime:
    next_day = (now_utc + timedelta(days=1)).date()
    return datetime.combine(next_day, time.min, tzinfo=timezone.utc)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    owner_uuid = uuid.UUID(user.user_id)

    existing_stmt = select(Workspace).where(Workspace.owner_id == owner_uuid).limit(1)
    existing_workspace = db.execute(existing_stmt).scalar_one_or_none()
    if existing_workspace:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "User already has a workspace",
                "workspace_id": str(existing_workspace.id),
            },
        )

    today_utc = datetime.now(timezone.utc).date()
    workspace = Workspace(name=payload.name.strip(), owner_id=owner_uuid)
    db.add(workspace)
    db.flush()

    usage_row = WorkspaceDailyUsage(
        workspace_id=workspace.id,
        date=today_utc,
        tokens_used=0,
        tokens_reserved=0,
    )
    db.add(usage_row)
    # TODO: Add outbox/event hooks after workspace creation.
    db.commit()
    db.refresh(workspace)

    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        owner_id=str(workspace.owner_id),
        created_at=workspace.created_at,
    )


@router.get("/me", response_model=WorkspaceMeResponse)
def get_my_workspace(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMeResponse:
    owner_uuid = uuid.UUID(user.user_id)

    workspace_stmt = select(Workspace).where(Workspace.owner_id == owner_uuid).limit(1)
    workspace = db.execute(workspace_stmt).scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Workspace isolation: all document queries are scoped by workspace_id.
    document_count_stmt = select(func.count(Document.id)).where(Document.workspace_id == workspace.id)
    document_count = db.execute(document_count_stmt).scalar_one() or 0

    status_counts_stmt = (
        select(Document.status, func.count(Document.id))
        .where(Document.workspace_id == workspace.id)
        .group_by(Document.status)
    )
    status_rows = db.execute(status_counts_stmt).all()
    documents_by_status = {str(status): int(count) for status, count in status_rows}

    today_utc: date = datetime.now(timezone.utc).date()
    usage_stmt = select(WorkspaceDailyUsage).where(
        WorkspaceDailyUsage.workspace_id == workspace.id,
        WorkspaceDailyUsage.date == today_utc,
    )
    usage = db.execute(usage_stmt).scalar_one_or_none()
    if usage is None:
        usage = WorkspaceDailyUsage(
            workspace_id=workspace.id,
            date=today_utc,
            tokens_used=0,
            tokens_reserved=0,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)

    remaining = max(0, settings.DAILY_TOKEN_LIMIT - int(usage.tokens_used) - int(usage.tokens_reserved))
    now_utc = datetime.now(timezone.utc)

    return WorkspaceMeResponse(
        id=str(workspace.id),
        name=workspace.name,
        owner_id=str(workspace.owner_id),
        created_at=workspace.created_at,
        document_count=int(document_count),
        documents_by_status=documents_by_status,
        usage_today=UsageTodayResponse(
            tokens_used=int(usage.tokens_used),
            tokens_reserved=int(usage.tokens_reserved),
            limit=settings.DAILY_TOKEN_LIMIT,
            remaining=remaining,
            resets_at=_utc_resets_at(now_utc),
        ),
    )
