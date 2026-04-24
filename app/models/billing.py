"""
Cobranza / Cuentas por cobrar.
- Invoice: cuenta por cobrar (puede venir de pedido, entrega, o ser manual)
- Payment: pagos parciales o totales
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Numeric, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base

SCHEMA = "hecorp_schema"


class Invoice(Base):
    __tablename__ = "billing_invoices"
    __table_args__ = (
        Index("ix_inv_status_due", "status", "due_date"),
        {"schema": SCHEMA},
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)        # CXC-2026-0001

    # cliente: puede ser de Aleaciones (clients) o de reparto (delivery_customers)
    # guardamos sólo el snapshot para no acoplar; se puede ampliar luego
    customer_kind = Column(String(20), nullable=False, default="aleaciones")  # aleaciones | reparto | manual
    customer_id = Column(Integer, nullable=True)
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(160), nullable=True)
    customer_phone = Column(String(30), nullable=True)

    # origen
    source_kind = Column(String(20), nullable=True)  # order | delivery | manual
    source_id = Column(Integer, nullable=True)
    source_code = Column(String(60), nullable=True)  # PED-…, ENT-…

    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)

    subtotal = Column(Numeric(14, 2), nullable=False, default=0)
    tax = Column(Numeric(14, 2), nullable=False, default=0)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    paid = Column(Numeric(14, 2), nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="MXN")

    # status: pendiente | parcial | pagada | vencida | cancelada
    status = Column(String(20), nullable=False, default="pendiente")

    notes = Column(Text, nullable=True)
    last_reminder_at = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    payments = relationship("Payment", back_populates="invoice",
                            cascade="all,delete-orphan",
                            order_by="Payment.paid_at")

    @property
    def balance(self):
        return float(self.total or 0) - float(self.paid or 0)

    @property
    def days_overdue(self) -> int:
        if self.status in ("pagada", "cancelada"):
            return 0
        delta = (datetime.utcnow() - self.due_date).total_seconds() / 86400.0
        return int(delta) if delta > 0 else 0


class Payment(Base):
    __tablename__ = "billing_payments"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey(f"{SCHEMA}.billing_invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    method = Column(String(30), nullable=False, default="efectivo")  # efectivo|transferencia|tarjeta|cheque|otro
    reference = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_email = Column(String(120), nullable=True)

    invoice = relationship("Invoice", back_populates="payments")
