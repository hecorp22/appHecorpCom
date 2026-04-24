from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

CFG = ConfigDict(from_attributes=True)


class InvoiceIn(BaseModel):
    customer_kind: str = "aleaciones"
    customer_id: Optional[int] = None
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    source_kind: Optional[str] = None
    source_id: Optional[int] = None
    source_code: Optional[str] = None
    due_date: datetime
    subtotal: Decimal
    tax: Decimal = Decimal("0")
    total: Decimal
    currency: str = "MXN"
    notes: Optional[str] = None


class PaymentIn(BaseModel):
    amount: Decimal
    method: str = "efectivo"
    reference: Optional[str] = None
    note: Optional[str] = None
    paid_at: Optional[datetime] = None


class PaymentOut(BaseModel):
    model_config = CFG
    id: int
    invoice_id: int
    amount: Decimal
    method: str
    reference: Optional[str]
    note: Optional[str]
    paid_at: datetime
    user_email: Optional[str]


class InvoiceOut(BaseModel):
    model_config = CFG
    id: int
    code: str
    customer_kind: str
    customer_id: Optional[int]
    customer_name: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    source_kind: Optional[str]
    source_id: Optional[int]
    source_code: Optional[str]
    issue_date: datetime
    due_date: datetime
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    paid: Decimal
    currency: str
    status: str
    notes: Optional[str]
    last_reminder_at: Optional[datetime]
    reminder_count: int
    created_at: datetime
    balance: float = 0
    days_overdue: int = 0
    payments: List[PaymentOut] = []


class InvoiceFromDelivery(BaseModel):
    delivery_id: int
    due_days: int = 7      # vence en N días
    tax_pct: Decimal = Decimal("0")
    notes: Optional[str] = None
