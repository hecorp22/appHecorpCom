from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

MODEL_CFG = ConfigDict(from_attributes=True)


# ---------- Driver ----------
class DriverIn(BaseModel):
    name: str = Field(..., max_length=120)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=120)
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    active: Optional[int] = 1
    notes: Optional[str] = None


class DriverOut(DriverIn):
    model_config = MODEL_CFG
    id: int
    created_at: datetime
    last_lat: Optional[float] = None
    last_lng: Optional[float] = None
    last_seen_at: Optional[datetime] = None
    track_token: Optional[str] = None


# ---------- Customer ----------
class DeliveryCustomerIn(BaseModel):
    name: str = Field(..., max_length=160)
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: str
    reference: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    kind: str = "cliente"
    notes: Optional[str] = None


class DeliveryCustomerOut(DeliveryCustomerIn):
    model_config = MODEL_CFG
    id: int
    created_at: datetime


# ---------- Delivery ----------
class DeliveryIn(BaseModel):
    customer_id: int
    run_id: Optional[int] = None
    driver_id: Optional[int] = None
    stop_order: int = 1
    scheduled_at: Optional[datetime] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    eta_at: Optional[datetime] = None
    status: str = "pendiente"
    product_summary: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "MXN"
    payment_status: str = "pendiente"
    ticket_number: Optional[str] = None
    invoice_url: Optional[str] = None
    ticket_url: Optional[str] = None
    delivery_message: Optional[str] = None


class DeliveryOut(BaseModel):
    model_config = MODEL_CFG
    id: int
    code: str
    run_id: Optional[int]
    driver_id: Optional[int]
    customer_id: int
    stop_order: int
    scheduled_at: Optional[datetime]
    window_start: Optional[datetime]
    window_end: Optional[datetime]
    eta_at: Optional[datetime]
    status: str
    arrived_at: Optional[datetime]
    delivered_at: Optional[datetime]
    product_summary: Optional[str]
    amount: Optional[Decimal]
    currency: str
    payment_status: str
    ticket_number: Optional[str]
    invoice_url: Optional[str]
    ticket_url: Optional[str]
    signature_url: Optional[str]
    photo_url: Optional[str]
    delivery_message: Optional[str]
    delivery_report: Optional[str]
    issue_code: Optional[str]
    issue_detail: Optional[str]
    is_late: bool = False
    created_at: datetime
    # opcional para embebido
    customer: Optional[DeliveryCustomerOut] = None
    driver: Optional[DriverOut] = None


# ---------- Run ----------
class DeliveryRunIn(BaseModel):
    name: str
    scheduled_date: datetime
    driver_id: Optional[int] = None
    ruta_id: Optional[int] = None
    status: str = "programada"
    notes: Optional[str] = None


class DeliveryRunOut(BaseModel):
    model_config = MODEL_CFG
    id: int
    code: str
    name: str
    scheduled_date: datetime
    driver_id: Optional[int]
    ruta_id: Optional[int]
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    total_stops: int
    completed_stops: int
    notes: Optional[str]
    created_at: datetime
    driver: Optional[DriverOut] = None
    deliveries: List[DeliveryOut] = []
