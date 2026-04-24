from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True)
    quote_code = Column(String(32), unique=True, nullable=False, index=True)

    # Datos del cliente / destinatario
    company = Column(String(160), nullable=False)           # Empresa
    contact_name = Column(String(160), nullable=False)      # Encargado
    email = Column(String(160), nullable=False)
    phone = Column(String(40), nullable=True)
    subject = Column(String(200), nullable=False)           # Asunto

    # Vínculo opcional a cliente existente
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)

    # Financiero
    currency = Column(String(8), default="MXN", nullable=False)
    iva_rate = Column(Numeric(5, 4), default=0.16, nullable=False)   # 0.16 = 16%
    subtotal = Column(Numeric(14, 2), default=0, nullable=False)
    iva_amount = Column(Numeric(14, 2), default=0, nullable=False)
    total = Column(Numeric(14, 2), default=0, nullable=False)

    status = Column(String(32), default="borrador", nullable=False)  # borrador, enviada, aceptada, rechazada
    valid_until = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationItem.id",
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)

    product = Column(String(160), nullable=False)          # Producto (ej. "Buje bronce 1/2\"")
    piece = Column(String(120), nullable=True)             # Descripción de la pieza / número de parte
    quantity = Column(Numeric(14, 3), default=1, nullable=False)

    # Tipo de venta: "pieza" o "kg"
    price_mode = Column(String(8), default="pieza", nullable=False)
    unit_price = Column(Numeric(14, 4), default=0, nullable=False)   # precio por pieza ó por kg
    weight_kg = Column(Numeric(14, 3), nullable=True)                # opcional, solo si price_mode=kg
    line_total = Column(Numeric(14, 2), default=0, nullable=False)

    notes = Column(String(255), nullable=True)

    quotation = relationship("Quotation", back_populates="items")
