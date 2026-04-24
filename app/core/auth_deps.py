"""Dependencias reutilizables de autorización."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User
from app.routers.auth_router import get_current_user_from_cookie


def require_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Requiere usuario autenticado (cualquier rol)."""
    return get_current_user_from_cookie(request, db)


def require_admin(
    user: User = Depends(require_user),
) -> User:
    """Requiere usuario con rol 'superuser' o 'admin'."""
    role = (user.role or "").lower()
    if role not in ("superuser", "admin"):
        raise HTTPException(status_code=403, detail="Acceso restringido")
    return user
