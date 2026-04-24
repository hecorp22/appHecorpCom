from typing import List
from fastapi import APIRouter, Depends, Form, UploadFile, File, Query

from app.schemas.shipment_schema import ShipmentCreate, ShipmentOut
from app.services.shipment_service import ShipmentService
from app.core.deps import get_shipment_service
from app.core.auth_deps import require_admin, require_user
from app.models.user_model import User

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("", response_model=List[ShipmentOut])
@router.get("/", response_model=List[ShipmentOut])
def list_shipments(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_user),
):
    return svc.list(limit=limit, offset=offset)


@router.get("/{shipment_id}", response_model=ShipmentOut)
def get_shipment(
    shipment_id: int,
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_user),
):
    return svc.get(shipment_id)


@router.post("", response_model=ShipmentOut)
@router.post("/", response_model=ShipmentOut)
def create_shipment(
    data: ShipmentCreate,
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_admin),
):
    return svc.create(data)


@router.post("/{shipment_id}/photos", response_model=ShipmentOut)
async def upload_photos(
    shipment_id: int,
    files: List[UploadFile] = File(...),
    caption: str = Form(""),
    send_sms_flag: bool = Form(False),
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_admin),
):
    ship = svc.get(shipment_id)
    ship = svc.save_photos(ship, files, caption=caption or None)
    if send_sms_flag and ship.recipient_phone:
        ship = svc.send_notification(ship)
    return ship


@router.post("/{shipment_id}/send-sms")
def resend_sms(
    shipment_id: int,
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_admin),
):
    ship = svc.get(shipment_id)
    ship = svc.send_notification(ship)
    return {"ok": ship.sms_sent, "error": ship.sms_error}


@router.patch("/{shipment_id}/status")
def update_status(
    shipment_id: int,
    status: str = Form(...),
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_admin),
):
    ship = svc.get(shipment_id)
    svc.update_status(ship, status)
    return {"ok": True, "status": status}


@router.delete("/{shipment_id}")
def delete_shipment(
    shipment_id: int,
    svc: ShipmentService = Depends(get_shipment_service),
    _: User = Depends(require_admin),
):
    svc.delete(shipment_id)
    return {"ok": True}
