"""
Servicio de entregas (delivery) — víveres/tortillas/paquetes.
Genera códigos, controla estado, detecta retrasos, notifica admin.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.delivery import Driver, DeliveryCustomer, Delivery, DeliveryRun
from app.services.admin_notify import _send as admin_send
from app.services.sms_service import send_sms


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _next_code(db: Session, prefix: str, model, field) -> str:
    year = datetime.utcnow().year
    last = (
        db.query(func.max(field))
        .filter(field.like(f"{prefix}-{year}-%"))
        .scalar()
    )
    n = 1
    if last:
        try:
            n = int(str(last).split("-")[-1]) + 1
        except Exception:
            n = 1
    return f"{prefix}-{year}-{n:04d}"


# --------------------------------------------------------------------------- #
# Driver CRUD
# --------------------------------------------------------------------------- #
def list_drivers(db: Session, active: Optional[int] = None) -> List[Driver]:
    q = db.query(Driver)
    if active is not None:
        q = q.filter(Driver.active == active)
    return q.order_by(Driver.name).all()


def create_driver(db: Session, data: Dict[str, Any]) -> Driver:
    d = Driver(**data)
    db.add(d); db.commit(); db.refresh(d)
    return d


def update_driver(db: Session, driver_id: int, data: Dict[str, Any]) -> Driver:
    d = db.query(Driver).filter_by(id=driver_id).first()
    if not d:
        raise HTTPException(404, "Chofer no encontrado")
    for k, v in data.items():
        setattr(d, k, v)
    db.commit(); db.refresh(d)
    return d


def delete_driver(db: Session, driver_id: int) -> None:
    d = db.query(Driver).filter_by(id=driver_id).first()
    if not d:
        raise HTTPException(404, "Chofer no encontrado")
    db.delete(d); db.commit()


# --------------------------------------------------------------------------- #
# Customer CRUD
# --------------------------------------------------------------------------- #
def list_customers(db: Session, q: str = "", kind: Optional[str] = None) -> List[DeliveryCustomer]:
    query = db.query(DeliveryCustomer)
    if q:
        ilike = f"%{q}%"
        query = query.filter(
            (DeliveryCustomer.name.ilike(ilike)) |
            (DeliveryCustomer.address.ilike(ilike))
        )
    if kind:
        query = query.filter(DeliveryCustomer.kind == kind)
    return query.order_by(DeliveryCustomer.name).limit(300).all()


def create_customer(db: Session, data: Dict[str, Any]) -> DeliveryCustomer:
    c = DeliveryCustomer(**data)
    db.add(c); db.commit(); db.refresh(c)
    return c


def update_customer(db: Session, cid: int, data: Dict[str, Any]) -> DeliveryCustomer:
    c = db.query(DeliveryCustomer).filter_by(id=cid).first()
    if not c:
        raise HTTPException(404, "Cliente de reparto no encontrado")
    for k, v in data.items():
        setattr(c, k, v)
    db.commit(); db.refresh(c)
    return c


def delete_customer(db: Session, cid: int) -> None:
    c = db.query(DeliveryCustomer).filter_by(id=cid).first()
    if not c:
        raise HTTPException(404, "Cliente de reparto no encontrado")
    db.delete(c); db.commit()


# --------------------------------------------------------------------------- #
# Run (jornada)
# --------------------------------------------------------------------------- #
RUN_STATUSES = {"programada", "en_curso", "completada", "incidencia", "cancelada"}


def list_runs(db: Session, date_from: Optional[datetime] = None,
              date_to: Optional[datetime] = None,
              status: Optional[str] = None) -> List[DeliveryRun]:
    q = db.query(DeliveryRun)
    if date_from:
        q = q.filter(DeliveryRun.scheduled_date >= date_from)
    if date_to:
        q = q.filter(DeliveryRun.scheduled_date <= date_to)
    if status:
        q = q.filter(DeliveryRun.status == status)
    return q.order_by(DeliveryRun.scheduled_date.desc()).limit(200).all()


def get_run(db: Session, run_id: int) -> DeliveryRun:
    r = db.query(DeliveryRun).filter_by(id=run_id).first()
    if not r:
        raise HTTPException(404, "Jornada no encontrada")
    return r


def create_run(db: Session, data: Dict[str, Any]) -> DeliveryRun:
    r = DeliveryRun(
        code=_next_code(db, "RUN", DeliveryRun, DeliveryRun.code),
        **data,
    )
    db.add(r); db.commit(); db.refresh(r)
    return r


def update_run_status(db: Session, run_id: int, status: str) -> DeliveryRun:
    if status not in RUN_STATUSES:
        raise HTTPException(400, f"Status inválido. Permitidos: {RUN_STATUSES}")
    r = get_run(db, run_id)
    r.status = status
    if status == "en_curso" and not r.started_at:
        r.started_at = datetime.utcnow()
    if status in ("completada", "cancelada") and not r.ended_at:
        r.ended_at = datetime.utcnow()
    db.commit(); db.refresh(r)
    return r


def update_run_counters(db: Session, run_id: int) -> DeliveryRun:
    r = get_run(db, run_id)
    r.total_stops = db.query(Delivery).filter_by(run_id=run_id).count()
    r.completed_stops = db.query(Delivery).filter_by(run_id=run_id, status="entregado").count()
    db.commit(); db.refresh(r)
    return r


def delete_run(db: Session, run_id: int) -> None:
    r = get_run(db, run_id)
    db.delete(r); db.commit()


# --------------------------------------------------------------------------- #
# Delivery
# --------------------------------------------------------------------------- #
DELIVERY_STATUSES = {"pendiente", "en_ruta", "entregado", "fallida", "reprogramada", "cancelada"}


def list_deliveries(db: Session, run_id: Optional[int] = None,
                    driver_id: Optional[int] = None,
                    status: Optional[str] = None,
                    late_only: bool = False) -> List[Delivery]:
    q = db.query(Delivery)
    if run_id:
        q = q.filter(Delivery.run_id == run_id)
    if driver_id:
        q = q.filter(Delivery.driver_id == driver_id)
    if status:
        q = q.filter(Delivery.status == status)
    q = q.order_by(Delivery.stop_order, Delivery.id)
    items = q.limit(500).all()
    if late_only:
        items = [d for d in items if d.is_late]
    return items


def get_delivery(db: Session, did: int) -> Delivery:
    d = db.query(Delivery).filter_by(id=did).first()
    if not d:
        raise HTTPException(404, "Entrega no encontrada")
    return d


def create_delivery(db: Session, data: Dict[str, Any]) -> Delivery:
    customer = db.query(DeliveryCustomer).filter_by(id=data["customer_id"]).first()
    if not customer:
        raise HTTPException(400, "Cliente de reparto no existe")
    if data.get("run_id"):
        if not db.query(DeliveryRun).filter_by(id=data["run_id"]).first():
            raise HTTPException(400, "Jornada no existe")
    if data.get("driver_id"):
        if not db.query(Driver).filter_by(id=data["driver_id"]).first():
            raise HTTPException(400, "Chofer no existe")

    d = Delivery(
        code=_next_code(db, "ENT", Delivery, Delivery.code),
        **data,
    )
    db.add(d); db.commit(); db.refresh(d)
    if d.run_id:
        update_run_counters(db, d.run_id)

    # notificar admin
    try:
        admin_send(
            "delivery_created",
            f"Nueva entrega {d.code}",
            f"HECORP • Entrega\nCódigo: {d.code}\nCliente: {customer.name}\nDirección: {customer.address}"
            + (f"\nProducto: {d.product_summary}" if d.product_summary else "")
            + (f"\nProgramado: {d.scheduled_at}" if d.scheduled_at else ""),
        )
    except Exception:
        pass
    return d


def update_delivery(db: Session, did: int, data: Dict[str, Any]) -> Delivery:
    d = get_delivery(db, did)
    for k, v in data.items():
        setattr(d, k, v)
    db.commit(); db.refresh(d)
    if d.run_id:
        update_run_counters(db, d.run_id)
    return d


def change_delivery_status(db: Session, did: int, status: str,
                           message: Optional[str] = None,
                           report: Optional[str] = None,
                           issue_code: Optional[str] = None,
                           issue_detail: Optional[str] = None) -> Delivery:
    if status not in DELIVERY_STATUSES:
        raise HTTPException(400, f"Status inválido. Permitidos: {DELIVERY_STATUSES}")
    d = get_delivery(db, did)
    d.status = status
    now = datetime.utcnow()
    if status == "en_ruta" and not d.arrived_at:
        d.arrived_at = now
    if status == "entregado" and not d.delivered_at:
        d.delivered_at = now
        if not d.arrived_at:
            d.arrived_at = now
    if message is not None:
        d.delivery_message = message
    if report is not None:
        d.delivery_report = report
    if issue_code is not None:
        d.issue_code = issue_code
    if issue_detail is not None:
        d.issue_detail = issue_detail
    db.commit(); db.refresh(d)

    if d.run_id:
        update_run_counters(db, d.run_id)

    # SMS al cliente cuando se marca en_ruta/entregado (si tiene tel)
    try:
        cust = d.customer
        if cust and cust.phone and status in ("en_ruta", "entregado"):
            if status == "en_ruta":
                body = (f"Hola {cust.contact_name or cust.name}, tu pedido va en camino. "
                        f"Folio {d.code}. Te avisamos al llegar.")
            else:
                body = (f"Pedido {d.code} entregado. Gracias {cust.contact_name or cust.name}.")
            send_sms(cust.phone, body)
    except Exception:
        pass

    # Aviso al admin si falla o hay incidencia
    try:
        if status in ("fallida", "reprogramada"):
            admin_send("delivery_issue",
                       f"Entrega {d.code} · {status}",
                       f"Entrega {d.code} marcada {status}. {(issue_detail or '')[:200]}")
    except Exception:
        pass
    return d


def delete_delivery(db: Session, did: int) -> None:
    d = get_delivery(db, did)
    run_id = d.run_id
    db.delete(d); db.commit()
    if run_id:
        update_run_counters(db, run_id)


# --------------------------------------------------------------------------- #
# KPI / dashboard
# --------------------------------------------------------------------------- #
def kpi_today(db: Session) -> Dict[str, Any]:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    runs_today = db.query(DeliveryRun).filter(
        DeliveryRun.scheduled_date >= today,
        DeliveryRun.scheduled_date < tomorrow,
    ).count()

    total = db.query(Delivery).filter(
        Delivery.scheduled_at >= today,
        Delivery.scheduled_at < tomorrow,
    ).count()

    by_status = {}
    for row in (db.query(Delivery.status, func.count(Delivery.id))
                .filter(Delivery.scheduled_at >= today,
                        Delivery.scheduled_at < tomorrow)
                .group_by(Delivery.status).all()):
        by_status[row[0]] = row[1]

    # late = todas las no entregadas con eta/window_end/scheduled < now
    now = datetime.utcnow()
    late = [d for d in db.query(Delivery).filter(
        Delivery.status.notin_(["entregado", "cancelada"]),
        Delivery.scheduled_at >= today,
        Delivery.scheduled_at < tomorrow,
    ).all() if d.is_late]

    return {
        "date": today.date().isoformat(),
        "runs_today": runs_today,
        "deliveries_today": total,
        "by_status": by_status,
        "late_count": len(late),
        "late_codes": [d.code for d in late[:10]],
    }
