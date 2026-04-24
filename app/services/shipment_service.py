import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile

from app.models.shipment import Shipment, ShipmentPhoto
from app.repos.shipment_repo import ShipmentRepo, ShipmentPhotoRepo
from app.repos.client_repo import ClientRepo
from app.repos.order_repo import OrderRepo
from app.schemas.shipment_schema import ShipmentCreate
from app.services.sms_service import send_sms, build_shipment_sms
from app.services.admin_notify import notify_shipment_created

UPLOAD_DIR = Path("app/static/uploads/shipments")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


class ShipmentService:
    def __init__(
        self,
        repo: ShipmentRepo,
        photo_repo: ShipmentPhotoRepo,
        client_repo: ClientRepo,
        order_repo: OrderRepo,
    ):
        self.repo = repo
        self.photo_repo = photo_repo
        self.client_repo = client_repo
        self.order_repo = order_repo

    # ---- listados ----
    def list(self, limit: int = 200, offset: int = 0) -> List[Shipment]:
        return self.repo.list(limit=limit, offset=offset)

    def get(self, shipment_id: int) -> Shipment:
        s = self.repo.by_id(shipment_id)
        if not s:
            raise HTTPException(status_code=404, detail="Envío no encontrado")
        return s

    # ---- creación ----
    def create(self, data: ShipmentCreate) -> Shipment:
        if not self.client_repo.exists(data.client_id):
            raise HTTPException(status_code=400, detail="Cliente no existe")
        if data.order_id and not self.order_repo.exists(data.order_id):
            raise HTTPException(status_code=400, detail="Pedido no existe")

        ship = Shipment(
            client_id=data.client_id,
            order_id=data.order_id,
            tracking_code=data.tracking_code,
            carrier=data.carrier,
            recipient_name=data.recipient_name,
            recipient_phone=data.recipient_phone,
            destination=data.destination,
            city=data.city,
            state=data.state,
            country=data.country,
            product_type=data.product_type,
            weight_kg=data.weight_kg,
            status=data.status,
            estimated_delivery=data.estimated_delivery,
            shipped_at=data.shipped_at,
            notes=data.notes,
        )
        ship = self.repo.add(ship)

        try:
            notify_shipment_created(ship)
        except Exception:
            pass

        if data.send_sms and ship.recipient_phone:
            self.send_notification(ship)

        return ship

    # ---- fotos ----
    def save_photos(self, shipment: Shipment, files: List[UploadFile], caption: Optional[str] = None) -> Shipment:
        for f in (files or [])[:5]:
            url = self._save_photo(shipment.id, f)
            if url:
                self.photo_repo.add(ShipmentPhoto(
                    shipment_id=shipment.id,
                    url=url,
                    caption=caption or None,
                ))
        self.repo.refresh(shipment)
        return shipment

    def _save_photo(self, shipment_id: int, upload: UploadFile) -> Optional[str]:
        if not upload or not upload.filename:
            return None
        ext = Path(upload.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=f"Formato no permitido: {ext}")
        name = f"ship-{shipment_id}-{uuid.uuid4().hex[:8]}{ext}"
        dest = UPLOAD_DIR / name
        dest.write_bytes(upload.file.read())
        return f"/static/uploads/shipments/{name}"

    # ---- status ----
    def update_status(self, shipment: Shipment, status: str) -> Shipment:
        allowed = {"preparando", "en_transito", "entregado", "incidencia", "cancelado"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail=f"status inválido ({allowed})")
        shipment.status = status
        if status == "entregado":
            shipment.delivered_at = datetime.utcnow()
        self.repo.commit()
        try:
            ctx_process_type.set("shipment")
            audit(self.repo.db, "update_status", "success",
                  {"shipment_id": shipment.id, "status": status})
        except Exception:
            pass
        return shipment

    def delete(self, shipment_id: int) -> None:
        ship = self.get(shipment_id)
        self.repo.delete(ship)
        try:
            ctx_process_type.set("shipment")
            audit(self.repo.db, "delete", "success", {"shipment_id": shipment_id})
        except Exception:
            pass

    # ---- tracking publico ----
    def by_tracking_public(self, code: str) -> Shipment:
        s = self.repo.by_tracking(code.strip())
        if not s:
            raise HTTPException(status_code=404, detail="Guia no encontrada")
        return s

    # ---- SMS ----
    def send_notification(self, ship: Shipment) -> Shipment:
        if not ship.recipient_phone:
            raise HTTPException(status_code=400, detail="Envío sin teléfono de destinatario")

        base = os.getenv("VPS_URL", "").strip() or "http://127.0.0.1:8000"
        photo_urls = [p.url for p in ship.photos]
        order_code = ship.order.order_code if ship.order else None
        eta = ship.estimated_delivery.strftime("%Y-%m-%d") if ship.estimated_delivery else None
        weight = float(ship.weight_kg) if ship.weight_kg is not None else None

        body = build_shipment_sms(
            public_base_url=base,
            order_code=order_code,
            tracking_code=ship.tracking_code,
            carrier=ship.carrier,
            weight_kg=weight,
            estimated_delivery=eta,
            destination=f"{ship.destination}, {ship.city}, {ship.state}",
            photo_urls=photo_urls,
        )
        ok, _sid, err = send_sms(ship.recipient_phone, body)
        ship.sms_sent = ok
        ship.sms_sent_at = datetime.utcnow() if ok else None
        ship.sms_error = err
        self.repo.commit()
        return ship
