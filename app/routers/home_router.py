from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

from app.routers.auth_router import get_current_user_from_cookie
from app.models.user_model import User
from app.settings import settings

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/home")
def home(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "vps_url": settings.VPS_URL,
            "user": user,
        }
    )
