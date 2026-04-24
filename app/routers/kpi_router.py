"""
KPIs para dashboard admin.
"""
from collections import Counter
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.core.auth_deps import require_user
from app.models.user_model import User
from app.models.client import Client
from app.models.provider import Provider
from app.models.order import Order
from app.models.shipment import Shipment

router = APIRouter(prefix="/admin/kpis", tags=["kpis"])


@router.get("")
def kpis(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
):
    now = datetime.utcnow()
    start_month = datetime(now.year, now.month, 1)

    orders_this_month = db.query(Order).filter(Order.created_at >= start_month).count()
    shipments_this_month = db.query(Shipment).filter(Shipment.created_at >= start_month).count()

    shipments_by_status = dict(
        db.query(Shipment.status, func.count(Shipment.id)).group_by(Shipment.status).all()
    )
    orders_by_status = dict(
        db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    )

    # Peso total enviado el mes
    total_weight = db.query(func.coalesce(func.sum(Shipment.weight_kg), 0)).filter(
        Shipment.created_at >= start_month
    ).scalar()

    return {
        "counts": {
            "clients": db.query(Client).count(),
            "providers": db.query(Provider).count(),
            "orders": db.query(Order).count(),
            "shipments": db.query(Shipment).count(),
        },
        "this_month": {
            "orders": orders_this_month,
            "shipments": shipments_this_month,
            "weight_kg": float(total_weight or 0),
        },
        "shipments_by_status": shipments_by_status,
        "orders_by_status": orders_by_status,
    }
