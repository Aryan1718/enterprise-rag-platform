from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CitationSourceResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    chunk_text: str
    page_text: str | None = None
    highlights: list[str] = Field(default_factory=list)


class DocumentPageSourceResponse(BaseModel):
    document_id: uuid.UUID
    page_number: int
    text: str
