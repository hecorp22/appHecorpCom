# app/policies/roles.py
from enum import Enum
from typing import Optional

class Role(str, Enum):
    SUPERUSER = "SUPERUSER"
    USER = "USER"

def is_superuser(user) -> bool:
    return getattr(user, "role", "").upper() == Role.SUPERUSER.value

def can_access_route(user, route_owner_id: str, shared_perm: Optional[str]) -> bool:
    """Devuelve True si user puede leer la ruta (owner / superuser / shared viewer/editor)"""
    if not user:
        return False
    if is_superuser(user):
        return True
    if str(getattr(user, "id", "")) == str(route_owner_id):
        return True
    if shared_perm in ("viewer", "editor"):
        return True
    return False

def can_edit_route(user, route_owner_id: str, shared_perm: Optional[str]) -> bool:
    if is_superuser(user):
        return True
    if str(getattr(user, "id", "")) == str(route_owner_id):
        return True
    if shared_perm == "editor":
        return True
    return False
