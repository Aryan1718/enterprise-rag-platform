import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UploadPrepareRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    file_size_bytes: int = Field(gt=0)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class UploadPrepareResponse(BaseModel):
    document_id: uuid.UUID
    bucket: str
    storage_path: str
    upload_url: str
    expires_in: int


class UploadCompleteRequest(BaseModel):
    document_id: uuid.UUID
    bucket: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=2048)


class UploadCompleteResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    job_id: str


class DocumentJobResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    job_id: str


class DocumentListItem(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    limit: int
    offset: int
    total: int


class DocumentProgress(BaseModel):
    pages_total: int
    pages_extracted_count: int
    chunks_count: int
    embeddings_count: int


class DocumentDetailResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: str
    bucket: str
    storage_path: str
    created_at: datetime
    updated_at: datetime
    progress: DocumentProgress
