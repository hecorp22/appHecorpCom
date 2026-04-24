from typing import List, Optional
from app.models.shipment import Shipment, ShipmentPhoto
from app.repos.base_repo import BaseRepo


class ShipmentRepo(BaseRepo[Shipment]):
    model = Shipment

    def by_tracking(self, code: str) -> Optional[Shipment]:
        return self.db.query(Shipment).filter(Shipment.tracking_code == code).first()

    def list_by_client(self, client_id: int) -> List[Shipment]:
        return (
            self.db.query(Shipment)
            .filter(Shipment.client_id == client_id)
            .order_by(Shipment.id.desc())
            .all()
        )


class ShipmentPhotoRepo(BaseRepo[ShipmentPhoto]):
    model = ShipmentPhoto
