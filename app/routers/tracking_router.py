"""
Tracking publico: vista sin autenticacion por codigo de guia.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.shipment_service import ShipmentService
from app.core.deps import get_shipment_service
from app.core.audit import audit
from app.core.context import ctx_process_type

router = APIRouter(tags=["tracking"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/track/{tracking_code}", response_class=HTMLResponse)
def track_public(
    tracking_code: str,
    request: Request,
    svc: ShipmentService = Depends(get_shipment_service),
):
    s = svc.by_tracking_public(tracking_code)
    try:
        ctx_process_type.set("tracking")
        audit(svc.repo.db, "view", "success",
              {"shipment_id": s.id, "tracking": s.tracking_code})
    except Exception:
        pass
    return templates.TemplateResponse("track_public.html", {
        "request": request,
        "s": s,
    })


@router.get("/api/track/{tracking_code}")
def track_api(
    tracking_code: str,
    svc: ShipmentService = Depends(get_shipment_service),
):
    s = svc.by_tracking_public(tracking_code)
    return {
        "tracking_code": s.tracking_code,
        "carrier": s.carrier,
        "recipient_name": s.recipient_name,
        "destination": s.destination,
        "city": s.city,
        "state": s.state,
        "country": s.country,
        "product_type": s.product_type,
        "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None,
        "status": s.status,
        "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
        "shipped_at": s.shipped_at.isoformat() if s.shipped_at else None,
        "delivered_at": s.delivered_at.isoformat() if s.delivered_at else None,
        "photos": [p.url for p in s.photos],
    }
