"""
Servicio de cobranza.
- CRUD de facturas/CXC
- Pagos parciales/totales con auto-cierre cuando saldo = 0
- Recordatorios escalonados (3 días antes / día / 7 / 15 / 30 después)
- Genera CXC desde una entrega con un click
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.billing import Invoice, Payment
from app.services.admin_notify import _send as admin_send
from app.services.sms_service import send_sms

ZERO = Decimal("0")

# umbrales de recordatorio en días respecto a due_date
# negativos = antes; positivos = después del vencimiento
REMINDER_OFFSETS = [-3, 0, 7, 15, 30]
COOLDOWN_HOURS = 20   # no reenvía 2 veces el mismo recordatorio en N horas


def _next_code(db: Session) -> str:
    year = datetime.utcnow().year
    last = (db.query(func.max(Invoice.code))
            .filter(Invoice.code.like(f"CXC-{year}-%"))
            .scalar())
    n = 1
    if last:
        try:
            n = int(str(last).split("-")[-1]) + 1
        except Exception:
            n = 1
    return f"CXC-{year}-{n:04d}"


def _recompute_status(inv: Invoice) -> None:
    paid = Decimal(inv.paid or 0)
    total = Decimal(inv.total or 0)
    if inv.status == "cancelada":
        return
    if paid >= total and total > 0:
        inv.status = "pagada"
    elif paid > 0 and paid < total:
        inv.status = "parcial"
        if inv.due_date and inv.due_date < datetime.utcnow():
            inv.status = "vencida"   # vencida puede ser parcial también; la marcamos vencida prioritario
    else:
        if inv.due_date and inv.due_date < datetime.utcnow():
            inv.status = "vencida"
        else:
            inv.status = "pendiente"


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def list_invoices(db: Session, status: Optional[str] = None,
                  q: str = "", overdue_only: bool = False,
                  limit: int = 200) -> List[Invoice]:
    query = db.query(Invoice)
    if status:
        query = query.filter(Invoice.status == status)
    if q:
        ilike = f"%{q}%"
        query = query.filter(
            (Invoice.code.ilike(ilike)) |
            (Invoice.customer_name.ilike(ilike)) |
            (Invoice.source_code.ilike(ilike))
        )
    if overdue_only:
        query = query.filter(
            Invoice.status.notin_(["pagada", "cancelada"]),
            Invoice.due_date < datetime.utcnow(),
        )
    return query.order_by(Invoice.due_date).limit(limit).all()


def get_invoice(db: Session, iid: int) -> Invoice:
    inv = db.query(Invoice).filter_by(id=iid).first()
    if not inv:
        raise HTTPException(404, "CXC no encontrada")
    return inv


def create_invoice(db: Session, data: Dict[str, Any]) -> Invoice:
    inv = Invoice(code=_next_code(db), **data)
    _recompute_status(inv)
    db.add(inv); db.commit(); db.refresh(inv)
    try:
        admin_send(
            "invoice_created",
            f"Nueva CXC {inv.code}",
            f"HECORP · Cobranza\nFolio: {inv.code}\nCliente: {inv.customer_name}\n"
            f"Total: {inv.total} {inv.currency}\nVence: {inv.due_date.strftime('%Y-%m-%d')}",
        )
    except Exception:
        pass
    return inv


def from_delivery(db: Session, delivery_id: int, due_days: int = 7,
                  tax_pct: Decimal = ZERO,
                  notes: Optional[str] = None) -> Invoice:
    """Genera una CXC a partir de una entrega ya existente."""
    from app.models.delivery import Delivery
    d = db.query(Delivery).filter_by(id=delivery_id).first()
    if not d:
        raise HTTPException(404, "Entrega no encontrada")
    if not d.amount or Decimal(d.amount) <= 0:
        raise HTTPException(400, "La entrega no tiene monto")

    cust = d.customer
    subtotal = Decimal(d.amount)
    tax = (subtotal * Decimal(tax_pct) / Decimal("100")).quantize(Decimal("0.01"))
    total = subtotal + tax

    data = dict(
        customer_kind="reparto",
        customer_id=cust.id if cust else None,
        customer_name=cust.name if cust else "—",
        customer_email=cust.email if cust else None,
        customer_phone=cust.phone if cust else None,
        source_kind="delivery",
        source_id=d.id,
        source_code=d.code,
        due_date=datetime.utcnow() + timedelta(days=due_days),
        subtotal=subtotal,
        tax=tax,
        total=total,
        currency=d.currency or "MXN",
        notes=notes,
    )
    return create_invoice(db, data)


def cancel_invoice(db: Session, iid: int) -> Invoice:
    inv = get_invoice(db, iid)
    inv.status = "cancelada"
    db.commit(); db.refresh(inv)
    return inv


# --------------------------------------------------------------------------- #
# Pagos
# --------------------------------------------------------------------------- #
def add_payment(db: Session, invoice_id: int, data: Dict[str, Any],
                user_email: Optional[str] = None) -> Payment:
    inv = get_invoice(db, invoice_id)
    if inv.status == "cancelada":
        raise HTTPException(400, "CXC cancelada")
    amount = Decimal(data["amount"])
    if amount <= 0:
        raise HTTPException(400, "amount debe ser > 0")
    balance = Decimal(inv.total) - Decimal(inv.paid)
    if amount > balance + Decimal("0.01"):
        raise HTTPException(400,
            f"Pago {amount} excede el saldo {balance}")

    p = Payment(
        invoice_id=inv.id,
        amount=amount,
        method=data.get("method", "efectivo"),
        reference=data.get("reference"),
        note=data.get("note"),
        paid_at=data.get("paid_at") or datetime.utcnow(),
        user_email=user_email,
    )
    db.add(p)
    inv.paid = Decimal(inv.paid) + amount
    _recompute_status(inv)
    db.commit(); db.refresh(p); db.refresh(inv)

    # SMS gracias al cliente si quedó saldada
    try:
        if inv.status == "pagada" and inv.customer_phone:
            send_sms(inv.customer_phone,
                     f"HECORP · {inv.code} pagada en su totalidad. "
                     f"Gracias {inv.customer_name}.")
        admin_send(
            "payment_received",
            f"Pago en {inv.code} · {amount} {inv.currency}",
            f"Pago de {amount} {inv.currency} aplicado a {inv.code}.\n"
            f"Saldo restante: {Decimal(inv.total)-Decimal(inv.paid)} {inv.currency}\n"
            f"Status: {inv.status}",
        )
    except Exception:
        pass
    return p


def delete_payment(db: Session, payment_id: int) -> None:
    p = db.query(Payment).filter_by(id=payment_id).first()
    if not p:
        raise HTTPException(404, "Pago no encontrado")
    inv = p.invoice
    inv.paid = max(Decimal("0"), Decimal(inv.paid) - Decimal(p.amount))
    db.delete(p)
    _recompute_status(inv)
    db.commit()


# --------------------------------------------------------------------------- #
# Recordatorios automáticos (cron)
# --------------------------------------------------------------------------- #
def _reminder_text(inv: Invoice, days_diff: int) -> str:
    """days_diff < 0 → próximas; = 0 día del vto; > 0 vencido."""
    name = inv.customer_name or "cliente"
    if days_diff < 0:
        return (f"HECORP · Recordatorio amistoso\nHola {name}, su factura {inv.code} "
                f"por {inv.total} {inv.currency} vence en {abs(days_diff)} día(s) "
                f"({inv.due_date.strftime('%Y-%m-%d')}).")
    if days_diff == 0:
        return (f"HECORP · Vence hoy\nHola {name}, su factura {inv.code} "
                f"por {inv.total} {inv.currency} vence hoy. Saldo: "
                f"{Decimal(inv.total)-Decimal(inv.paid)} {inv.currency}.")
    return (f"HECORP · Factura vencida\nHola {name}, su factura {inv.code} tiene "
            f"{days_diff} día(s) de vencida. Saldo: "
            f"{Decimal(inv.total)-Decimal(inv.paid)} {inv.currency}. "
            f"Por favor regularice. Gracias.")


def run_reminders(db: Session) -> Dict[str, Any]:
    """
    Recorre CXC abiertas y manda SMS al cliente + correo al admin
    cuando coincide con un offset y el cooldown lo permite.
    """
    now = datetime.utcnow()
    actives = (db.query(Invoice)
               .filter(Invoice.status.in_(["pendiente", "parcial", "vencida"]))
               .all())

    sent = []
    for inv in actives:
        # actualiza status si pasó vencimiento
        _recompute_status(inv)

        days_diff = int((now.date() - inv.due_date.date()).days)
        if days_diff not in REMINDER_OFFSETS:
            continue

        # cooldown: no más de 1 recordatorio del mismo offset cada COOLDOWN_HOURS
        if inv.last_reminder_at and (
            (now - inv.last_reminder_at) < timedelta(hours=COOLDOWN_HOURS)
        ):
            continue

        body = _reminder_text(inv, days_diff)
        sent_ok = False
        try:
            if inv.customer_phone:
                send_sms(inv.customer_phone, body)
                sent_ok = True
        except Exception:
            pass
        try:
            admin_send(
                "invoice_reminder",
                f"Recordatorio {inv.code} · {days_diff:+d}d",
                body + f"\n\nCliente: {inv.customer_name}\n"
                       f"Tel: {inv.customer_phone or '—'}",
            )
            sent_ok = True
        except Exception:
            pass

        if sent_ok:
            inv.last_reminder_at = now
            inv.reminder_count = (inv.reminder_count or 0) + 1
            sent.append({
                "code": inv.code, "days_diff": days_diff,
                "customer": inv.customer_name,
                "balance": float(Decimal(inv.total) - Decimal(inv.paid)),
            })

    db.commit()
    return {"checked_at": now.isoformat(), "sent": len(sent), "items": sent}


# --------------------------------------------------------------------------- #
# KPIs
# --------------------------------------------------------------------------- #
def kpi_billing(db: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # actualizar status venidos
    for inv in (db.query(Invoice)
                .filter(Invoice.status.in_(["pendiente", "parcial"]),
                        Invoice.due_date < now).all()):
        _recompute_status(inv)
    db.commit()

    by_status = {}
    for row in (db.query(Invoice.status, func.count(Invoice.id),
                          func.coalesce(func.sum(Invoice.total - Invoice.paid), 0))
                .group_by(Invoice.status).all()):
        by_status[row[0]] = {"count": row[1], "outstanding": float(row[2])}

    # cobrado del mes
    paid_month = (db.query(func.coalesce(func.sum(Payment.amount), 0))
                  .filter(Payment.paid_at >= month_start).scalar() or 0)

    # total por cobrar abierto
    outstanding = (db.query(func.coalesce(func.sum(Invoice.total - Invoice.paid), 0))
                   .filter(Invoice.status.in_(["pendiente", "parcial", "vencida"]))
                   .scalar() or 0)

    overdue = (db.query(func.count(Invoice.id))
               .filter(Invoice.status == "vencida").scalar() or 0)

    return {
        "outstanding": float(outstanding),
        "paid_month": float(paid_month),
        "overdue_count": int(overdue),
        "by_status": by_status,
    }
