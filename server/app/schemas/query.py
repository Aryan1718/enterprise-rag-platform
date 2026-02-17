import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    document_id: uuid.UUID
    question: str = Field(min_length=1, max_length=500)


class QueryCitation(BaseModel):
    document_id: uuid.UUID
    page_number: int
    chunk_id: uuid.UUID
    score: float
    snippet: str


class QueryUsage(BaseModel):
    limit: int
    used: int
    reserved: int
    remaining: int
    resets_at: datetime


class QueryResponse(BaseModel):
    answer: str
    citations: list[QueryCitation]
    usage: QueryUsage
