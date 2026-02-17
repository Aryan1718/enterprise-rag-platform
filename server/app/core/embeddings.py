from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

from app.config import settings


@dataclass
class EmbeddingResult:
    embedding: list[float]
    total_tokens: int


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=float(settings.LLM_TIMEOUT_SECONDS))


def embed_query_text(text: str) -> EmbeddingResult:
    response = _client().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )
    vector = response.data[0].embedding
    if len(vector) != settings.EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch: expected {settings.EMBEDDING_DIM}, got {len(vector)}"
        )
    usage = getattr(response, "usage", None)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    return EmbeddingResult(embedding=vector, total_tokens=total_tokens)
