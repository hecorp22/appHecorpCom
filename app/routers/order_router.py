from typing import List
from fastapi import APIRouter, Depends, Query, Form

from app.schemas.order_schema import OrderCreate, OrderOut
from app.services.order_service import OrderService
from app.core.deps import get_order_service
from app.core.auth_deps import require_admin, require_user
from app.models.user_model import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=List[OrderOut])
@router.get("/", response_model=List[OrderOut])
def list_orders(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: OrderService = Depends(get_order_service),
    _: User = Depends(require_user),
):
    return svc.list(limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    svc: OrderService = Depends(get_order_service),
    _: User = Depends(require_user),
):
    return svc.get(order_id)


@router.post("", response_model=OrderOut)
@router.post("/", response_model=OrderOut)
def create_order(
    data: OrderCreate,
    svc: OrderService = Depends(get_order_service),
    _: User = Depends(require_admin),
):
    return svc.create(data)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    status: str = Form(...),
    svc: OrderService = Depends(get_order_service),
    _: User = Depends(require_admin),
):
    return svc.update_status(order_id, status)


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    svc: OrderService = Depends(get_order_service),
    _: User = Depends(require_admin),
):
    svc.delete(order_id)
    return {"ok": True}
