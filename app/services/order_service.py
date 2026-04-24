from typing import List
from fastapi import HTTPException

from app.models.order import Order, OrderItem
from app.repos.order_repo import OrderRepo
from app.repos.client_repo import ClientRepo
from app.schemas.order_schema import OrderCreate, ITEM_TYPES
from app.core.audit import audit
from app.core.context import ctx_process_type
from app.services.admin_notify import notify_order_created


class OrderService:
    def __init__(self, repo: OrderRepo, client_repo: ClientRepo):
        self.repo = repo
        self.client_repo = client_repo

    def list(self, limit: int = 200, offset: int = 0) -> List[Order]:
        return self.repo.list(limit=limit, offset=offset)

    def get(self, order_id: int) -> Order:
        o = self.repo.by_id(order_id)
        if not o:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        return o

    def update_status(self, order_id: int, status: str) -> Order:
        allowed = {"pendiente", "en_proceso", "listo", "enviado", "cancelado"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail=f"status inv\u00e1lido ({allowed})")
        o = self.get(order_id)
        o.status = status
        self.repo.commit()
        try:
            ctx_process_type.set("order")
            audit(self.repo.db, "update_status", "success", {"order_id": o.id, "status": status})
        except Exception:
            pass
        return o

    def delete(self, order_id: int) -> None:
        o = self.get(order_id)
        self.repo.delete(o)
        try:
            ctx_process_type.set("order")
            audit(self.repo.db, "delete", "success", {"order_id": order_id})
        except Exception:
            pass

    def create(self, data: OrderCreate) -> Order:
        if not self.client_repo.exists(data.client_id):
            raise HTTPException(status_code=400, detail="Cliente no existe")

        for it in data.items:
            if it.item_type not in ITEM_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"item_type inválido: {it.item_type}",
                )

        order = Order(
            order_code=self.repo.next_order_code(),
            client_id=data.client_id,
            recipient_name=data.recipient_name,
            destination=data.destination,
            city=data.city,
            state=data.state,
            country=data.country or "México",
            status=data.status,
            total_weight_kg=data.total_weight_kg,
            estimated_delivery=data.estimated_delivery,
            notes=data.notes,
        )
        for it in data.items:
            order.items.append(OrderItem(
                item_type=it.item_type,
                description=it.description,
                quantity=it.quantity,
                unit_weight_kg=it.unit_weight_kg,
                unit_price=it.unit_price,
                notes=it.notes,
            ))
        saved = self.repo.add(order)
        try:
            ctx_process_type.set("order")
            audit(self.repo.db, "create", "success", {
                "order_id": saved.id,
                "order_code": saved.order_code,
                "client_id": saved.client_id,
                "items": len(saved.items),
            })
        except Exception:
            pass
        try:
            notify_order_created(saved)
        except Exception:
            pass
        return saved
