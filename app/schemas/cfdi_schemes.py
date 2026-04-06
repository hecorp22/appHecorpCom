# app/schemas/cfdi_schemes.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# =========================
# CFDI individuales
# =========================

class CFDIBase(BaseModel):
    version: Optional[str] = None
    serie: Optional[str] = None
    folio: Optional[str] = None
    fecha: Optional[datetime] = None

    forma_pago: Optional[str] = None
    metodo_pago: Optional[str] = None
    moneda: Optional[str] = None
    tipo_comprobante: Optional[str] = None
    lugar_expedicion: Optional[str] = Field(None, alias="lugarExpedicion")

    subtotal: Optional[float] = None
    descuento: Optional[float] = None
    total: Optional[float] = None

    emisor_rfc: Optional[str] = None
    emisor_nombre: Optional[str] = None
    emisor_regimen_fiscal: Optional[str] = None

    receptor_rfc: Optional[str] = None
    receptor_nombre: Optional[str] = None
    receptor_uso_cfdi: Optional[str] = None

    uuid: str
    fecha_timbrado: Optional[datetime] = None
    sello_cfd: Optional[str] = None
    sello_sat: Optional[str] = None
    no_certificado_sat: Optional[str] = None

    xml_raw: Optional[str] = None
    cadena_original: Optional[str] = None
    estado: Optional[str] = "ACTIVO"

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class CFDICreate(CFDIBase):
    """Datos listos para guardar después de parsear el XML."""
    pass


class CFDIRead(CFDIBase):
    id: str


# =========================
# Procesamiento masivo (ZIP)
# =========================

class CFDIBatchItem(BaseModel):
    filename: str
    uuid: Optional[str] = None
    status: str               # "created" | "duplicate" | "error" | "skipped"
    error: Optional[str] = None


class CFDIBatchResponse(BaseModel):
    total_files: int
    processed: int
    created: int
    duplicates: int
    failed: int
    skipped: int
    items: List[CFDIBatchItem]
