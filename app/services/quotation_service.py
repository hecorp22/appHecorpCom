from decimal import Decimal, ROUND_HALF_UP
from typing import List
from fastapi import HTTPException

from app.models.quotation import Quotation, QuotationItem
from app.repos.quotation_repo import QuotationRepo
from app.schemas.quotation_schema import QuotationCreate
from app.core.audit import audit
from app.core.context import ctx_process_type

TWOPLACES = Decimal("0.01")


def _money(x) -> Decimal:
    return Decimal(x).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class QuotationService:
    def __init__(self, repo: QuotationRepo):
        self.repo = repo

    def list(self, q: str = "", limit: int = 200, offset: int = 0) -> List[Quotation]:
        return self.repo.search(q, limit=limit, offset=offset)

    def get(self, quote_id: int) -> Quotation:
        o = self.repo.by_id(quote_id)
        if not o:
            raise HTTPException(status_code=404, detail="Cotización no encontrada")
        return o

    def _calc_item_total(self, it) -> Decimal:
        qty = Decimal(it.quantity or 0)
        price = Decimal(it.unit_price or 0)
        if it.price_mode == "kg":
            weight = Decimal(it.weight_kg or 0)
            # Total = qty * weight * price_kg
            return _money(qty * weight * price)
        return _money(qty * price)

    def create(self, data: QuotationCreate) -> Quotation:
        subtotal = Decimal("0.00")
        items: List[QuotationItem] = []
        for it in data.items:
            line = self._calc_item_total(it)
            subtotal += line
            items.append(QuotationItem(
                product=it.product,
                piece=it.piece,
                quantity=it.quantity,
                price_mode=it.price_mode,
                unit_price=it.unit_price,
                weight_kg=it.weight_kg,
                line_total=line,
                notes=it.notes,
            ))

        iva_rate = Decimal(data.iva_rate or 0)
        iva_amount = _money(subtotal * iva_rate)
        total = _money(subtotal + iva_amount)

        q = Quotation(
            quote_code=self.repo.next_code(),
            company=data.company,
            contact_name=data.contact_name,
            email=data.email,
            phone=data.phone,
            subject=data.subject,
            client_id=data.client_id,
            currency=data.currency or "MXN",
            iva_rate=iva_rate,
            subtotal=_money(subtotal),
            iva_amount=iva_amount,
            total=total,
            valid_until=data.valid_until,
            notes=data.notes,
            status="borrador",
        )
        for it in items:
            q.items.append(it)

        saved = self.repo.add(q)
        try:
            ctx_process_type.set("quotation")
            audit(self.repo.db, "create", "success", {
                "quotation_id": saved.id,
                "quote_code": saved.quote_code,
                "total": float(saved.total),
            })
        except Exception:
            pass
        return saved

    def update_status(self, quote_id: int, status: str) -> Quotation:
        allowed = {"borrador", "enviada", "aceptada", "rechazada"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail=f"status inválido ({allowed})")
        q = self.get(quote_id)
        q.status = status
        self.repo.commit()
        try:
            ctx_process_type.set("quotation")
            audit(self.repo.db, "update_status", "success",
                  {"quotation_id": q.id, "status": status})
        except Exception:
            pass
        return q

    def delete(self, quote_id: int) -> None:
        q = self.get(quote_id)
        self.repo.delete(q)
        try:
            ctx_process_type.set("quotation")
            audit(self.repo.db, "delete", "success", {"quotation_id": quote_id})
        except Exception:
            pass
