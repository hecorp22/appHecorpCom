from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import re

PHONE_RE = re.compile(r"^\d{10}$")


class ShipmentPhotoOut(BaseModel):
    id: int
    url: str
    caption: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ShipmentCreate(BaseModel):
    client_id: int = Field(..., ge=1)
    order_id: Optional[int] = Field(None, ge=1)

    tracking_code: str = Field(..., min_length=3, max_length=80)
    carrier: str = Field(..., min_length=2, max_length=60)

    recipient_name: str = Field(..., min_length=2, max_length=160)
    recipient_phone: Optional[str] = None

    destination: str = Field(..., min_length=3, max_length=255)
    city: str = Field(..., min_length=2, max_length=80)
    state: str = Field(..., min_length=2, max_length=80)
    country: str = Field("México", max_length=80)

    product_type: str = Field(..., min_length=2, max_length=80)
    weight_kg: Optional[Decimal] = Field(None, ge=0)

    status: str = Field("preparando", pattern="^(preparando|en_transito|entregado|incidencia|cancelado)$")
    estimated_delivery: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    notes: Optional[str] = None

    send_sms: bool = True  # si true → se manda SMS al crear si hay teléfono

    @field_validator("recipient_phone")
    @classmethod
    def v_phone(cls, v):
        if v in (None, "", " "):
            return None
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("Teléfono debe tener 10 dígitos")
        return v


class ShipmentOut(BaseModel):
    id: int
    client_id: int
    order_id: Optional[int] = None
    tracking_code: str
    carrier: str
    recipient_name: str
    recipient_phone: Optional[str] = None
    destination: str
    city: str
    state: str
    country: str
    product_type: str
    weight_kg: Optional[Decimal] = None
    status: str
    estimated_delivery: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    sms_sent: bool = False
    sms_error: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    photos: List[ShipmentPhotoOut] = []
    model_config = ConfigDict(from_attributes=True)
