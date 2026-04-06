# app/models/cfdi_model_sat.py
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

from app.database import Base  # IMPORTANTE: usar el mismo Base

class CFDI(Base):
    __tablename__ = "cfdi"
    __table_args__ = {"schema": "hecorp_schema"}  # 👈 IMPORTAMOS SCHEME
    

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    version = Column(String(10), nullable=True)
    serie = Column(String(25), nullable=True)
    folio = Column(String(40), nullable=True)
    fecha = Column(DateTime, nullable=True)

    forma_pago = Column(String(10), nullable=True)
    metodo_pago = Column(String(10), nullable=True)
    moneda = Column(String(10), nullable=True)
    tipo_comprobante = Column(String(2), nullable=True)
    lugar_expedicion = Column(String(10), nullable=True)

    subtotal = Column(Numeric(16, 2), nullable=True)
    descuento = Column(Numeric(16, 2), nullable=True)
    total = Column(Numeric(16, 2), nullable=True)

    emisor_rfc = Column(String(13), nullable=True, index=True)
    emisor_nombre = Column(String(255), nullable=True)
    emisor_regimen_fiscal = Column(String(5), nullable=True)

    receptor_rfc = Column(String(13), nullable=True, index=True)
    receptor_nombre = Column(String(255), nullable=True)
    receptor_uso_cfdi = Column(String(5), nullable=True)

    uuid = Column(String(36), nullable=False, unique=True, index=True)
    fecha_timbrado = Column(DateTime, nullable=True)
    sello_cfd = Column(Text, nullable=True)
    sello_sat = Column(Text, nullable=True)
    no_certificado_sat = Column(String(20), nullable=True)

    xml_raw = Column(Text, nullable=True)
    cadena_original = Column(Text, nullable=True)

    estado = Column(String(20), nullable=True, default="ACTIVO")
    intentos_validacion = Column(Integer, nullable=False, default=0)
