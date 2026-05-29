from fastapi import Depends, HTTPException, status

from app.models import User
from app.services.auth import get_current_user


def require_roles(*allowed_roles: str):
    allowed = set(allowed_roles)

    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return current_user

    return _dep
