from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


ITEM_TYPES = {"buje", "hule", "portachumacera", "flecha", "maquinado", "otro"}


class OrderItemIn(BaseModel):
    item_type: str = Field(..., description="buje|hule|portachumacera|flecha|maquinado|otro")
    description: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., ge=1, le=10000)
    unit_weight_kg: Optional[Decimal] = Field(None, ge=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=255)

    @classmethod
    def validate_type(cls, v):
        if v not in ITEM_TYPES:
            raise ValueError(f"item_type inválido, usa: {sorted(ITEM_TYPES)}")
        return v


class OrderItemOut(OrderItemIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    client_id: int = Field(..., ge=1)
    recipient_name: str = Field(..., min_length=2, max_length=160)
    destination: str = Field(..., min_length=3, max_length=255)
    city: Optional[str] = Field(None, max_length=80)
    state: Optional[str] = Field(None, max_length=80)
    country: Optional[str] = Field("México", max_length=80)

    status: str = Field("pendiente", pattern="^(pendiente|en_proceso|listo|enviado|cancelado)$")
    total_weight_kg: Optional[Decimal] = Field(None, ge=0)
    estimated_delivery: Optional[datetime] = None
    notes: Optional[str] = None

    items: List[OrderItemIn] = Field(..., min_length=1)


class OrderOut(BaseModel):
    id: int
    order_code: str
    client_id: int
    recipient_name: str
    destination: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    status: str
    total_weight_kg: Optional[Decimal] = None
    estimated_delivery: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    items: List[OrderItemOut] = []
    model_config = ConfigDict(from_attributes=True)
