"""
Módulo de ENTREGAS (delivery) — para monitoreo de rutas de camionetas
que reparten víveres/tortillas/paquetes.
Independiente del módulo Shipment (que es de Aleaciones y Maquinados).
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Numeric, Index,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

SCHEMA = "hecorp_schema"


# --------------------------------------------------------------------------- #
# Driver (chofer / encargado de ruta)
# --------------------------------------------------------------------------- #
class Driver(Base):
    __tablename__ = "delivery_drivers"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    vehicle_plate = Column(String(20), nullable=True)
    vehicle_type = Column(String(60), nullable=True)     # camioneta, moto, bici, a pie
    active = Column(Integer, nullable=False, default=1)  # 1/0
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # tracking en vivo
    last_lat = Column(Float, nullable=True)
    last_lng = Column(Float, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    track_token = Column(String(64), nullable=True, unique=True)  # para PWA del chofer

    deliveries = relationship("Delivery", back_populates="driver")
    runs = relationship("DeliveryRun", back_populates="driver")
    pings = relationship("DriverPing", back_populates="driver", cascade="all,delete-orphan")


# --------------------------------------------------------------------------- #
# DriverPing (histórico de coordenadas en vivo)
# --------------------------------------------------------------------------- #
class DriverPing(Base):
    __tablename__ = "delivery_driver_pings"
    __table_args__ = (
        Index("ix_pings_driver_time", "driver_id", "ts"),
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey(f"{SCHEMA}.delivery_drivers.id", ondelete="CASCADE"), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)            # m/s
    accuracy = Column(Float, nullable=True)         # metros
    heading = Column(Float, nullable=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow)

    driver = relationship("Driver", back_populates="pings")


# --------------------------------------------------------------------------- #
# DeliveryCustomer (clientes de reparto, distintos de clientes de Aleaciones)
# --------------------------------------------------------------------------- #
class DeliveryCustomer(Base):
    __tablename__ = "delivery_customers"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)       # nombre del negocio/persona
    contact_name = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    address = Column(String(300), nullable=False)
    reference = Column(String(300), nullable=True)   # "tienda amarilla, frente a OXXO"
    city = Column(String(80), nullable=True)
    state = Column(String(80), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    kind = Column(String(40), nullable=False, default="cliente")   # cliente | proveedor
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    deliveries = relationship("Delivery", back_populates="customer")


# --------------------------------------------------------------------------- #
# DeliveryRun (jornada — un día de ruta)
# --------------------------------------------------------------------------- #
class DeliveryRun(Base):
    __tablename__ = "delivery_runs"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey(f"{SCHEMA}.delivery_drivers.id", ondelete="SET NULL"), nullable=True)
    ruta_id = Column(Integer, ForeignKey(f"{SCHEMA}.rutas.id", ondelete="SET NULL"), nullable=True)

    # status global: programada | en_curso | completada | incidencia | cancelada
    status = Column(String(30), nullable=False, default="programada")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    total_stops = Column(Integer, nullable=False, default=0)
    completed_stops = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    driver = relationship("Driver", back_populates="runs")
    deliveries = relationship("Delivery", back_populates="run", order_by="Delivery.stop_order")


# --------------------------------------------------------------------------- #
# Delivery (una parada)
# --------------------------------------------------------------------------- #
class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        Index("ix_deliveries_status_eta", "status", "eta_at"),
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)
    run_id = Column(Integer, ForeignKey(f"{SCHEMA}.delivery_runs.id", ondelete="CASCADE"), nullable=True)
    driver_id = Column(Integer, ForeignKey(f"{SCHEMA}.delivery_drivers.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(Integer, ForeignKey(f"{SCHEMA}.delivery_customers.id", ondelete="CASCADE"), nullable=False)

    stop_order = Column(Integer, nullable=False, default=1)     # orden dentro de la jornada
    # programación
    scheduled_at = Column(DateTime, nullable=True)              # hora planeada de paso
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    eta_at = Column(DateTime, nullable=True)                    # ETA actual (calculada)

    # cumplimiento
    # status: pendiente | en_ruta | entregado | fallida | reprogramada | cancelada
    status = Column(String(30), nullable=False, default="pendiente")
    arrived_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # contenido
    product_summary = Column(String(240), nullable=True)        # "3 cajas tortilla, 10 salsas"
    amount = Column(Numeric(12, 2), nullable=True)              # monto a cobrar (opc)
    currency = Column(String(8), nullable=False, default="MXN")
    payment_status = Column(String(20), nullable=False, default="pendiente")   # pendiente | pagado | credito

    # artefactos
    ticket_number = Column(String(60), nullable=True)           # folio/ticket físico
    invoice_url = Column(String(500), nullable=True)            # factura PDF
    ticket_url = Column(String(500), nullable=True)
    signature_url = Column(String(500), nullable=True)          # firma/foto
    photo_url = Column(String(500), nullable=True)
    delivery_message = Column(Text, nullable=True)              # mensaje que deja el chofer
    delivery_report = Column(Text, nullable=True)               # reporte cierre

    # incidencia
    issue_code = Column(String(40), nullable=True)              # cerrado, ausente, rechazo
    issue_detail = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    run = relationship("DeliveryRun", back_populates="deliveries")
    driver = relationship("Driver", back_populates="deliveries")
    customer = relationship("DeliveryCustomer", back_populates="deliveries")

    # ---- helpers ----
    @property
    def is_late(self) -> bool:
        if self.status in ("entregado", "cancelada"):
            return False
        reference = self.eta_at or self.window_end or self.scheduled_at
        if not reference:
            return False
        return datetime.utcnow() > reference
