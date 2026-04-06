from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.rutas import Ruta
from app.schemas.rutas_schema import RutaCreate, RutaUpdate, RutaOut
from app.routers.auth_router import get_current_user_from_cookie

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="", tags=["rutas"])

# =============== HTML (Admin) ===============
@router.get("/rutas", response_class=HTMLResponse)
def rutas_admin(
    request: Request,
    user: str = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Buscar por nombre"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    query = db.query(Ruta).filter(Ruta.user_id == str(user))
    if q:
        query = query.filter(Ruta.nombre.ilike(f"%{q}%"))
    total = query.count()
    rutas = query.order_by(Ruta.created_at.desc()).offset((page-1)*size).limit(size).all()
    return templates.TemplateResponse(
        "rutas_admin.html",
        {
            "request": request,
            "user": user,
            "rutas": rutas,
            "q": q or "",
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size
        }
    )

# =============== API JSON ===============
api = APIRouter(prefix="/api/rutas", tags=["rutas-API"])

@api.get("", response_model=List[RutaOut])
def listar_rutas(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user_from_cookie),
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    query = db.query(Ruta).filter(Ruta.user_id == str(user))
    if q:
        query = query.filter(Ruta.nombre.ilike(f"%{q}%"))
    return query.order_by(Ruta.created_at.desc()).offset((page-1)*size).limit(size).all()

@api.get("/{ruta_id}", response_model=RutaOut)
def obtener_ruta(
    ruta_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user_from_cookie),
):
    ruta = db.query(Ruta).filter(Ruta.id == ruta_id, Ruta.user_id == str(user)).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return ruta

@api.post("", response_model=RutaOut)
def crear_ruta(
    payload: RutaCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user_from_cookie),
):
    ruta = Ruta(
        nombre=payload.nombre,
        user_id=str(user),
        origen_lat=payload.origen_lat, origen_lng=payload.origen_lng,
        destino_lat=payload.destino_lat, destino_lng=payload.destino_lng,
        distancia_km=payload.distancia_km, duracion_min=payload.duracion_min,
        geojson=payload.geojson, notas=payload.notas
    )
    db.add(ruta)
    db.commit()
    db.refresh(ruta)
    return ruta

@api.patch("/{ruta_id}", response_model=RutaOut)
def actualizar_ruta(
    ruta_id: int,
    payload: RutaUpdate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user_from_cookie),
):
    ruta = db.query(Ruta).filter(Ruta.id == ruta_id, Ruta.user_id == str(user)).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(ruta, k, v)
    db.commit()
    db.refresh(ruta)
    return ruta

@api.delete("/{ruta_id}")
def eliminar_ruta(
    ruta_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user_from_cookie),
):
    ruta = db.query(Ruta).filter(Ruta.id == ruta_id, Ruta.user_id == str(user)).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    db.delete(ruta)
    db.commit()
    return {"ok": True}

# Registra routers en main
# app.include_router(router)
# app.include_router(api)
