from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_documents() -> dict[str, list[dict[str, str]]]:
    # TODO: Implement document listing with workspace isolation.
    return {"items": []}
