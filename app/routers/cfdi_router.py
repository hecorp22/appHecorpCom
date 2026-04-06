# app/routers/cfdi_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.cfdi_model_sat import CFDI
from app.schemas.cfdi_schemes import (
    CFDICreate,
    CFDIRead,
    CFDIBatchResponse,
)
from app.services.cfdi.parser_cfdi import parse_cfdi_xml
from app.services.cfdi.cfdi_service import (
    create_or_get_cfdi_from_xml,
    process_cfdi_zip,
)

router = APIRouter(
    prefix="/cfdi",
    tags=["CFDI SAT"],
)


# Dependencia de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== ENDPOINT: XML individual ==========

@router.post(
    "/xml",
    response_model=CFDIRead,
    status_code=status.HTTP_201_CREATED,
)
async def subir_cfdi_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .xml")

    xml_content = await file.read()

    try:
        cfdi_obj, is_created = create_or_get_cfdi_from_xml(db, xml_content)
        db.commit()
        db.refresh(cfdi_obj)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"XML inválido: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar XML: {str(e)}")

    return cfdi_obj


# ========== ENDPOINT: ZIP con múltiples XML ==========

@router.post(
    "/xml/zip",
    response_model=CFDIBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subir_cfdi_zip(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    📦 Sube un ZIP que contenga múltiples XML de CFDI.
    Devuelve un resumen de lo procesado.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .zip")

    zip_bytes = await file.read()

    try:
        result = process_cfdi_zip(db, zip_bytes)
    except ValueError as e:
        # errores de ZIP inválido
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar ZIP: {e}")

    return result


# ========== ENDPOINTS de consulta ==========

@router.get("/", response_model=List[CFDIRead])
def listar_cfdi(
    db: Session = Depends(get_db),
    emisor_rfc: Optional[str] = None,
    receptor_rfc: Optional[str] = None,
    uuid: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(CFDI)

    if emisor_rfc:
        query = query.filter(CFDI.emisor_rfc == emisor_rfc)
    if receptor_rfc:
        query = query.filter(CFDI.receptor_rfc == receptor_rfc)
    if uuid:
        query = query.filter(CFDI.uuid == uuid)

    return query.order_by(CFDI.fecha.desc()).offset(skip).limit(limit).all()


@router.get("/{uuid}", response_model=CFDIRead)
def obtener_cfdi(
    uuid: str,
    db: Session = Depends(get_db),
):
    cfdi = db.query(CFDI).filter(CFDI.uuid == uuid).first()
    if not cfdi:
        raise HTTPException(status_code=404, detail="CFDI no encontrado")
    return cfdi
