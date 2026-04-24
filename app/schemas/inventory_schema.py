from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

CFG = ConfigDict(from_attributes=True)


class WarehouseIn(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    is_default: int = 0
    active: int = 1


class WarehouseOut(WarehouseIn):
    model_config = CFG
    id: int
    created_at: datetime


class ProductIn(BaseModel):
    sku: str
    name: str
    unit: str = "pza"
    category: Optional[str] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    stock_min: Decimal = Decimal("0")
    active: int = 1
    notes: Optional[str] = None


class ProductOut(ProductIn):
    model_config = CFG
    id: int
    created_at: datetime
    total_qty: Optional[Decimal] = None        # suma stock en todos los almacenes
    low_stock: bool = False


class StockOut(BaseModel):
    model_config = CFG
    id: int
    product_id: int
    warehouse_id: int
    qty: Decimal
    updated_at: datetime
    product: Optional[ProductOut] = None
    warehouse: Optional[WarehouseOut] = None


class MovementIn(BaseModel):
    product_id: int
    warehouse_id: int
    kind: str       # entrada | salida | ajuste
    qty: Decimal
    reason: Optional[str] = None
    reference: Optional[str] = None


class MovementOut(BaseModel):
    model_config = CFG
    id: int
    product_id: int
    warehouse_id: int
    kind: str
    qty: Decimal
    reason: Optional[str]
    reference: Optional[str]
    user_email: Optional[str]
    ts: datetime
    product: Optional[ProductOut] = None
    warehouse: Optional[WarehouseOut] = None


class TransferIn(BaseModel):
    product_id: int
    from_wh: int
    to_wh: int
    qty: Decimal
    reason: Optional[str] = None


class DeliveryItemIn(BaseModel):
    product_id: int
    qty: Decimal
    price: Optional[Decimal] = None
    note: Optional[str] = None


class DeliveryItemOut(DeliveryItemIn):
    model_config = CFG
    id: int
    delivery_id: int
    product: Optional[ProductOut] = None
