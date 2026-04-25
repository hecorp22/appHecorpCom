"""Panel de monitoreo de seguridad (solo superuser)."""
from fastapi import APIRouter, Depends, Request, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers.auth_router import get_current_user_from_cookie
from app.core.security_middleware import get_security_snapshot, unblock_ip

templates = Jinja2Templates(directory="app/templates")

html = APIRouter(tags=["security"])
api = APIRouter(prefix="/api/security", tags=["security-api"])


def _require_superuser(user):
    role = getattr(user, "role", None) or (user if isinstance(user, str) else None)
    is_super = (getattr(user, "is_superuser", False)
                or role in ("superuser", "admin"))
    if not is_super:
        raise HTTPException(403, "Solo administradores")
    return user


@html.get("/admin/security", response_class=HTMLResponse)
def security_dashboard(request: Request,
                       user=Depends(get_current_user_from_cookie)):
    _require_superuser(user)
    snap = get_security_snapshot()
    return templates.TemplateResponse(
        "security_admin.html",
        {"request": request, "user": user, "snap": snap},
    )


@api.get("/snapshot")
def api_snapshot(user=Depends(get_current_user_from_cookie)):
    _require_superuser(user)
    return get_security_snapshot()


@api.post("/unblock")
def api_unblock(ip: str = Body(..., embed=True),
                user=Depends(get_current_user_from_cookie)):
    _require_superuser(user)
    return {"ok": unblock_ip(ip), "ip": ip}
