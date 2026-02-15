from fastapi import APIRouter

router = APIRouter()


@router.post("")
def run_query() -> dict[str, str]:
    # TODO: Implement strict grounded RAG query flow.
    return {"message": "Not implemented"}
