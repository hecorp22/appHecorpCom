from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Numeric, Text, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(30), unique=True, index=True, nullable=False)  # PED-0001
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Destinatario / destino a nivel pedido (puede diferir del cliente)
    recipient_name = Column(String(160), nullable=False)
    destination = Column(String(255), nullable=False)
    city = Column(String(80), nullable=True)
    state = Column(String(80), nullable=True)
    country = Column(String(80), nullable=True, default="México")

    status = Column(String(24), nullable=False, default="pendiente")
    # pendiente | en_proceso | listo | enviado | cancelado

    total_weight_kg = Column(Numeric(10, 3), nullable=True)
    estimated_delivery = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", lazy="joined")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    shipments = relationship(
        "Shipment",
        back_populates="order",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)

    item_type = Column(String(40), nullable=False)
    # buje | hule | portachumacera | flecha | maquinado | otro

    description = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_weight_kg = Column(Numeric(10, 3), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=True)
    notes = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="items")
