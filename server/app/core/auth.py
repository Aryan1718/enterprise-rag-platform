from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status
from supabase import Client, create_client

from app.config import settings


@dataclass
class AuthenticatedUser:
    user_id: str
    email: str | None = None
    role: str | None = None


def _supabase_client() -> Client:
    if not settings.SUPABASE_URL or not settings.supabase_service_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase auth is not configured",
        )
    return create_client(settings.SUPABASE_URL, settings.supabase_service_key)


def _fallback_get_user_via_rest(jwt_token: str) -> AuthenticatedUser:
    # TODO: Remove fallback once supabase/httpx dependency compatibility is stabilized.
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "apikey": settings.supabase_service_key,
    }
    response = httpx.get(url, headers=headers, timeout=10.0)
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    return AuthenticatedUser(
        user_id=str(user_id),
        email=payload.get("email"),
        role=payload.get("role"),
    )


# TODO: Add token validation caching to reduce auth round-trips.
def validate_jwt_and_get_user(jwt_token: str) -> AuthenticatedUser:
    try:
        response = _supabase_client().auth.get_user(jwt_token)
        user = getattr(response, "user", None)
        if user is None or not getattr(user, "id", None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            )

        return AuthenticatedUser(
            user_id=str(user.id),
            email=getattr(user, "email", None),
            role=getattr(user, "role", None),
        )
    except TypeError as exc:
        # Known issue in some supabase/httpx combinations: unexpected 'proxy' kwarg.
        if "proxy" in str(exc):
            return _fallback_get_user_via_rest(jwt_token)
        raise
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        detail = "Invalid or expired access token"
        if settings.environment == "development":
            detail = f"Invalid or expired access token: {exc}"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        ) from exc
