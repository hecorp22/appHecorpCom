"""
Export CSV de clientes, pedidos, envios.
"""
import csv
from io import StringIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.auth_deps import require_admin
from app.models.user_model import User
from app.services.client_service import ClientService
from app.services.order_service import OrderService
from app.services.shipment_service import ShipmentService
from app.core.deps import get_client_service, get_order_service, get_shipment_service

router = APIRouter(prefix="/admin/export", tags=["export"])


def _csv_response(rows, headers, filename):
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/clients.csv")
def export_clients(
    svc: ClientService = Depends(get_client_service),
    _: User = Depends(require_admin),
):
    rows = [[c.id, c.name, c.account_key, c.phone, c.address, c.city, c.state, c.country]
            for c in svc.list(limit=10000)]
    return _csv_response(rows,
        ["id", "name", "account_key", "phone", "address", "city", "state", "country"],
        "clients.csv")


@router.get("/orders.csv")
def export_orders(
    svc: OrderService = Depends(get_order_service),
    _: User = Depends(require_admin),
):
    rows = []
    for o in svc.list(limit=10000):
        rows.append([o.id, o.order_code, o.client_id, o.recipient_name,
                     o.destination, o.city, o.state, o.country, o.status,
                     float(o.total_weight_kg) if o.total_weight_kg is not None else "",
                     o.estimated_delivery.isoformat() if o.estimated_delivery else "",
                     o.created_at.isoformat() if o.created_at else "",
                     len(o.items)])
    return _csv_response(rows,
        ["id", "order_code", "client_id", "recipient_name", "destination",
         "city", "state", "country", "status", "weight_kg",
         "estimated_delivery", "created_at", "items"],
        "orders.csv")


@router.get("/shipments.csv")
def export_shipments(
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_admin),
):
    rows = []
    for s in svc.list(limit=10000):
        rows.append([s.id, s.tracking_code, s.carrier, s.client_id, s.order_id,
                     s.recipient_name, s.recipient_phone, s.destination,
                     s.city, s.state, s.country, s.product_type,
                     float(s.weight_kg) if s.weight_kg is not None else "",
                     s.status,
                     s.shipped_at.isoformat() if s.shipped_at else "",
                     s.delivered_at.isoformat() if s.delivered_at else "",
                     "yes" if s.sms_sent else "no"])
    return _csv_response(rows,
        ["id", "tracking", "carrier", "client_id", "order_id", "recipient",
         "phone", "destination", "city", "state", "country", "product_type",
         "weight_kg", "status", "shipped_at", "delivered_at", "sms_sent"],
        "shipments.csv")
