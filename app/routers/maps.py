# app/routers/maps.py — vista del mapa interactivo
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.routers.auth_router import get_current_user_from_cookie

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/maps", response_class=HTMLResponse)
def ver_maps(
    request: Request,
    user: str = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        "mapsRoutes.html",
        {"request": request, "user": user},
    )
