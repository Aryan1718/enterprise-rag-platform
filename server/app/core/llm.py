from dataclasses import dataclass
from functools import lru_cache
from typing import AsyncIterator

from openai import AsyncOpenAI, OpenAI

from app.config import settings
from app.core.prompts import grounded_system_prompt, grounded_user_prompt
from app.core.retrieval import RetrievedChunk


@dataclass
class LLMResult:
    answer: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class LLMStreamEvent:
    type: str
    text: str = ""
    result: LLMResult | None = None


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=float(settings.LLM_TIMEOUT_SECONDS))


@lru_cache(maxsize=1)
def _async_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=float(settings.LLM_TIMEOUT_SECONDS))


def answer_question_strict_grounded(question: str, chunks: list[RetrievedChunk]) -> LLMResult:
    response = _client().chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0,
        max_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": grounded_system_prompt()},
            {"role": "user", "content": grounded_user_prompt(question, chunks)},
        ],
    )
    content = ""
    if response.choices:
        content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
    return LLMResult(
        answer=content.strip(),
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


async def stream_answer_question_strict_grounded(
    question: str,
    chunks: list[RetrievedChunk],
) -> AsyncIterator[LLMStreamEvent]:
    kwargs = {
        "model": settings.LLM_MODEL,
        "temperature": 0,
        "max_tokens": settings.LLM_MAX_OUTPUT_TOKENS,
        "messages": [
            {"role": "system", "content": grounded_system_prompt()},
            {"role": "user", "content": grounded_user_prompt(question, chunks)},
        ],
        "stream": True,
    }
    try:
        stream = await _async_client().chat.completions.create(
            **kwargs,
            stream_options={"include_usage": True},
        )
    except TypeError:
        stream = await _async_client().chat.completions.create(**kwargs)

    answer_parts: list[str] = []
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    async for chunk in stream:
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            prompt_tokens = int(getattr(usage, "prompt_tokens", prompt_tokens) or prompt_tokens)
            completion_tokens = int(getattr(usage, "completion_tokens", completion_tokens) or completion_tokens)
            total_tokens = int(getattr(usage, "total_tokens", total_tokens) or total_tokens)

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        text = getattr(delta, "content", None) or ""
        if text:
            answer_parts.append(text)
            yield LLMStreamEvent(type="delta", text=text)

    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens

    yield LLMStreamEvent(
        type="done",
        result=LLMResult(
            answer="".join(answer_parts).strip(),
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )
