"""
Notificaciones al administrador: SMS (Twilio) y email (Resend).
Nunca tira excepción al caller: loguea y sigue.

Variables de entorno:
  ADMIN_NOTIFY_PHONE    teléfono admin (ej. +522712120182)
  ADMIN_NOTIFY_EMAIL    correo admin (opcional)
  ADMIN_NOTIFY_SMS      "1"/"true" para activar SMS admin (default: on si hay phone)
  ADMIN_NOTIFY_EMAIL_ON "1"/"true" para activar email admin (default: on si hay email)
"""
import os
import logging
from typing import Optional

from app.services.sms_service import send_sms
from app.services.email_service import send_email

logger = logging.getLogger("app.admin_notify")


def _truthy(v: Optional[str], default: bool) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _admin_phone() -> Optional[str]:
    p = os.getenv("ADMIN_NOTIFY_PHONE", "").strip()
    return p or None


def _admin_email() -> Optional[str]:
    e = os.getenv("ADMIN_NOTIFY_EMAIL", "").strip()
    return e or None


def _sms_enabled() -> bool:
    return _truthy(os.getenv("ADMIN_NOTIFY_SMS"), default=True) and bool(_admin_phone())


def _email_enabled() -> bool:
    return _truthy(os.getenv("ADMIN_NOTIFY_EMAIL_ON"), default=True) and bool(_admin_email())


def _send(kind: str, subject: str, body_sms: str, body_html: Optional[str] = None) -> None:
    """Entrega por SMS + email admin. Swallows errors."""
    # SMS
    if _sms_enabled():
        try:
            ok, sid, err = send_sms(_admin_phone(), body_sms)
            if ok:
                logger.info("admin_sms_sent kind=%s sid=%s", kind, sid)
            else:
                logger.warning("admin_sms_fail kind=%s err=%s", kind, err)
        except Exception:
            logger.exception("admin_sms_exception kind=%s", kind)
    # Email
    if _email_enabled():
        try:
            ok, mid, err = send_email(
                to=_admin_email(),
                subject=subject,
                text=body_sms,
                html=body_html or f"<pre style='font-family:system-ui;font-size:13px'>{body_sms}</pre>",
            )
            if ok:
                logger.info("admin_email_sent kind=%s id=%s", kind, mid)
            else:
                logger.warning("admin_email_fail kind=%s err=%s", kind, err)
        except Exception:
            logger.exception("admin_email_exception kind=%s", kind)


# ---------------------------------------------------------------------------
# Formatos por tipo
# ---------------------------------------------------------------------------

def notify_order_created(order) -> None:
    items = len(getattr(order, "items", []) or [])
    peso = getattr(order, "total_weight_kg", None)
    body = (
        f"HECORP • Nuevo PEDIDO\n"
        f"Código: {order.order_code}\n"
        f"Destino: {order.destination}, {order.city}, {order.state}\n"
        f"Items: {items}"
        + (f"\nPeso: {peso} kg" if peso else "")
        + (f"\nEntrega estimada: {order.estimated_delivery.strftime('%Y-%m-%d')}"
           if getattr(order, 'estimated_delivery', None) else "")
    )
    _send("order_created", f"Nuevo pedido {order.order_code}", body)


def notify_quotation_created(q) -> None:
    total = getattr(q, "total", None)
    cur = getattr(q, "currency", "MXN")
    body = (
        f"HECORP • Nueva COTIZACION\n"
        f"Código: {q.quote_code}\n"
        f"Empresa: {q.company}\n"
        f"Encargado: {q.contact_name}\n"
        f"Asunto: {q.subject}\n"
        + (f"Total: ${total} {cur}" if total is not None else "")
    )
    _send("quotation_created", f"Nueva cotización {q.quote_code}", body)


def notify_shipment_created(ship) -> None:
    order_code = ship.order.order_code if getattr(ship, "order", None) else "—"
    body = (
        f"HECORP • Nuevo ENVIO\n"
        f"Guía: {ship.tracking_code}\n"
        f"Pedido: {order_code}\n"
        f"Paquetería: {ship.carrier}\n"
        f"Destino: {ship.destination}, {ship.city}, {ship.state}"
        + (f"\nPeso: {ship.weight_kg} kg" if getattr(ship, 'weight_kg', None) else "")
    )
    _send("shipment_created", f"Nuevo envío {ship.tracking_code}", body)
