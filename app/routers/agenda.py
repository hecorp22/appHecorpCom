# app/routers/agenda_router.py
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud.agenda_crud import crear_evento, listar_eventos, actualizar_evento, eliminar_evento
from app.routers.auth_router import get_current_user_from_cookie
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

# Mostrar agenda
@router.get("/agenda", response_class=HTMLResponse)
def ver_agenda(request: 
    Request,user: str = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)):
    eventos = listar_eventos(db)
    return templates.TemplateResponse("agenda.html", {
        "request": request, "eventos": eventos,"user":user})

# Crear evento desde form
@router.post("/agenda/crear", response_class=HTMLResponse)
def crear_evento_form(
    request: Request,
    titulo: str = Form(...),
    descripcion: str = Form(None),
    fecha: str = Form(...),
    db: Session = Depends(get_db)
):
    from datetime import datetime
    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    crear_evento(db, titulo, descripcion, fecha_obj)
    eventos = listar_eventos(db)
    return templates.TemplateResponse("agenda.html", {"request": request, "eventos": eventos})
