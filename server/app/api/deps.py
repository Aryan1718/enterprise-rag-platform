import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser, validate_jwt_and_get_user
from app.db.models import Workspace
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return validate_jwt_and_get_user(credentials.credentials)


# TODO: Reuse this dependency for all workspace-scoped endpoints.
def get_workspace_id(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> uuid.UUID:
    stmt = select(Workspace.id).where(Workspace.owner_id == uuid.UUID(user.user_id)).limit(1)
    workspace_id = db.execute(stmt).scalar_one_or_none()
    if workspace_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace_id
