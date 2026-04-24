from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Numeric, Text, Boolean, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    tracking_code = Column(String(80), nullable=False, index=True)    # guía
    carrier = Column(String(60), nullable=False)                       # DHL / Estafeta / ...

    recipient_name = Column(String(160), nullable=False)
    recipient_phone = Column(String(20), nullable=True)

    destination = Column(String(255), nullable=False)
    city = Column(String(80), nullable=False)
    state = Column(String(80), nullable=False)
    country = Column(String(80), nullable=False, default="México")

    product_type = Column(String(80), nullable=False)   # bujes / hules / portachumaceras / flechas / maquinados / mixto
    weight_kg = Column(Numeric(10, 3), nullable=True)

    status = Column(String(24), nullable=False, default="preparando")
    # preparando | en_transito | entregado | incidencia | cancelado

    estimated_delivery = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime(timezone=True), nullable=True)
    sms_error = Column(String(255), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", lazy="joined")
    order = relationship("Order", back_populates="shipments", lazy="joined")
    photos = relationship(
        "ShipmentPhoto",
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ShipmentPhoto(Base):
    __tablename__ = "shipment_photos"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(512), nullable=False)
    caption = Column(String(160), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shipment = relationship("Shipment", back_populates="photos")
