"""
Inventario / Almacén HECORP.
- Product: catálogo de productos con SKU, unidad, precio, stock_min
- Warehouse: ubicaciones físicas
- Stock: cantidad de cada producto en cada almacén (tabla agregada, rápida)
- StockMovement: histórico de movimientos (entrada/salida/ajuste/transferencia)
- DeliveryItem: línea producto × cantidad por entrega (descuenta stock al entregar)
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Numeric,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base

SCHEMA = "hecorp_schema"


class Warehouse(Base):
    __tablename__ = "inv_warehouses"
    __table_args__ = {"schema": SCHEMA}
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    address = Column(String(300), nullable=True)
    is_default = Column(Integer, nullable=False, default=0)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "inv_products"
    __table_args__ = {"schema": SCHEMA}
    id = Column(Integer, primary_key=True)
    sku = Column(String(40), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    unit = Column(String(20), nullable=False, default="pza")     # pza, kg, caja, lt, m
    category = Column(String(80), nullable=True)
    price = Column(Numeric(12, 2), nullable=True)                # precio venta
    cost = Column(Numeric(12, 2), nullable=True)                 # costo
    stock_min = Column(Numeric(12, 2), nullable=False, default=0)
    active = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    stocks = relationship("Stock", back_populates="product",
                          cascade="all,delete-orphan")
    movements = relationship("StockMovement", back_populates="product")


class Stock(Base):
    __tablename__ = "inv_stocks"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_stock_prod_wh"),
        {"schema": SCHEMA},
    )
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey(f"{SCHEMA}.inv_products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey(f"{SCHEMA}.inv_warehouses.id", ondelete="CASCADE"), nullable=False)
    qty = Column(Numeric(14, 3), nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="stocks")
    warehouse = relationship("Warehouse")


class StockMovement(Base):
    __tablename__ = "inv_movements"
    __table_args__ = (
        Index("ix_mov_product_ts", "product_id", "ts"),
        {"schema": SCHEMA},
    )
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey(f"{SCHEMA}.inv_products.id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey(f"{SCHEMA}.inv_warehouses.id", ondelete="CASCADE"), nullable=False)
    # kind: entrada | salida | ajuste | transferencia_in | transferencia_out
    kind = Column(String(30), nullable=False)
    qty = Column(Numeric(14, 3), nullable=False)              # siempre positivo, kind define signo
    reason = Column(String(120), nullable=True)
    reference = Column(String(120), nullable=True)            # ej. ENT-2026-0001, COT-…, manual
    user_email = Column(String(120), nullable=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)

    product = relationship("Product", back_populates="movements")
    warehouse = relationship("Warehouse")


class DeliveryItem(Base):
    """Línea de producto en una entrega. Descuenta stock al cerrar."""
    __tablename__ = "delivery_items"
    __table_args__ = {"schema": SCHEMA}
    id = Column(Integer, primary_key=True)
    delivery_id = Column(Integer, ForeignKey(f"{SCHEMA}.deliveries.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey(f"{SCHEMA}.inv_products.id", ondelete="RESTRICT"), nullable=False)
    qty = Column(Numeric(14, 3), nullable=False, default=1)
    price = Column(Numeric(12, 2), nullable=True)             # precio aplicado
    note = Column(String(200), nullable=True)

    product = relationship("Product")
