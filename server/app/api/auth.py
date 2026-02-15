from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.auth import AuthenticatedUser

router = APIRouter()


@router.get("/me")
def get_me(user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, str | None]:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
    }
