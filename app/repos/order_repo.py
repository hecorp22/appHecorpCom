from typing import List, Optional
from app.models.order import Order, OrderItem
from app.repos.base_repo import BaseRepo


class OrderRepo(BaseRepo[Order]):
    model = Order

    def next_order_code(self) -> str:
        last = self.db.query(Order).order_by(Order.id.desc()).first()
        n = (last.id + 1) if last else 1
        return f"PED-{n:04d}"

    def list_by_client(self, client_id: int) -> List[Order]:
        return (
            self.db.query(Order)
            .filter(Order.client_id == client_id)
            .order_by(Order.id.desc())
            .all()
        )

    def by_code(self, code: str) -> Optional[Order]:
        return self.db.query(Order).filter(Order.order_code == code).first()
