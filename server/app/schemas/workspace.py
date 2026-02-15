from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime


class UsageTodayResponse(BaseModel):
    tokens_used: int
    tokens_reserved: int
    limit: int
    remaining: int
    resets_at: datetime


class WorkspaceMeResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime
    document_count: int
    documents_by_status: dict[str, int]
    usage_today: UsageTodayResponse
