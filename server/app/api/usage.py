from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_workspace_id
from app.core.token_budget import get_budget_status
from app.db.session import get_db
from app.schemas.usage import UsageTodayResponse

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
