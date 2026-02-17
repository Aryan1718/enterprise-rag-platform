from app.core.retrieval import RetrievedChunk

INSUFFICIENT_CONTEXT_MESSAGE = "Insufficient context in the provided documents."


def grounded_system_prompt() -> str:
    return (
        "You are a strict grounded assistant.\n"
        "Rules:\n"
        "1) Use only the provided context blocks.\n"
        "2) Do not use outside knowledge.\n"
        "3) Every factual claim must include citations in format [p<page>|chunk:<chunk_id>].\n"
        f"4) If the context does not support the answer, output exactly: {INSUFFICIENT_CONTEXT_MESSAGE}\n"
        "5) Never fabricate citations."
    )


def grounded_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_blocks: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"Context {idx}",
                    f"page: {chunk.page_number}",
                    f"chunk_id: {chunk.chunk_id}",
                    f"chunk_excerpt: {chunk.chunk_text}",
                    f"full_page_text: {chunk.page_text}",
                ]
            )
        )
    return "\n\n".join(
        [
            f"Question:\n{question}",
            "Context:",
            "\n\n".join(context_blocks),
            (
                "Answer using only the context above. "
                "Attach citations for all claims with [p<page>|chunk:<chunk_id>]."
            ),
        ]
    )
