from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


PRICE_MODES = ("pieza", "kg")


class QuotationItemIn(BaseModel):
    product: str = Field(..., min_length=1, max_length=160)
    piece: Optional[str] = Field(None, max_length=120)
    quantity: Decimal = Field(..., gt=0)
    price_mode: Literal["pieza", "kg"] = "pieza"
    unit_price: Decimal = Field(..., ge=0)
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=255)

    @field_validator("weight_kg")
    @classmethod
    def weight_if_kg(cls, v, info):
        if info.data.get("price_mode") == "kg" and (v is None or v <= 0):
            raise ValueError("weight_kg requerido si price_mode='kg'")
        return v


class QuotationItemOut(QuotationItemIn):
    id: int
    line_total: Decimal

    model_config = {"from_attributes": True}


class QuotationCreate(BaseModel):
    company: str = Field(..., min_length=2, max_length=160)
    contact_name: str = Field(..., min_length=2, max_length=160)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=40)
    subject: str = Field(..., min_length=2, max_length=200)
    client_id: Optional[int] = None
    currency: str = "MXN"
    iva_rate: Decimal = Decimal("0.16")
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[QuotationItemIn] = Field(..., min_length=1)


class QuotationOut(BaseModel):
    id: int
    quote_code: str
    company: str
    contact_name: str
    email: str
    phone: Optional[str] = None
    subject: str
    client_id: Optional[int] = None
    currency: str
    iva_rate: Decimal
    subtotal: Decimal
    iva_amount: Decimal
    total: Decimal
    status: str
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    items: List[QuotationItemOut] = []

    model_config = {"from_attributes": True}
