"""
SMS service vía Twilio. Tolerante a fallos: si no está configurado o falla,
devuelve (ok=False, error=...) en vez de tirar excepción.
"""
import os
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger("app.sms")

try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioRestException
except Exception:  # pragma: no cover
    TwilioClient = None
    TwilioRestException = Exception


def _cfg():
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    frm = os.getenv("TWILIO_SMS_FROM", "").split("#")[0].strip()  # por si hay comentario en .env
    return sid, tok, frm


def _normalize_mx(number: str) -> str:
    n = (number or "").strip()
    if not n:
        return n
    if n.startswith("+"):
        return n
    digits = "".join(c for c in n if c.isdigit())
    if len(digits) == 10:
        return "+52" + digits
    return "+" + digits


def send_sms(to: str, body: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Retorna (ok, sid|None, error|None)
    """
    sid, tok, frm = _cfg()
    if not (sid and tok and frm):
        return False, None, "Twilio no configurado (.env)"

    if TwilioClient is None:
        return False, None, "Paquete twilio no instalado"

    to_fmt = _normalize_mx(to)
    if not to_fmt:
        return False, None, "Teléfono destino vacío"

    try:
        client = TwilioClient(sid, tok)
        msg = client.messages.create(from_=frm, to=to_fmt, body=body[:1600])
        logger.info("sms_sent", extra={"to": to_fmt, "sid": msg.sid})
        return True, msg.sid, None
    except TwilioRestException as e:
        logger.error("sms_twilio_error", extra={"to": to_fmt, "error": str(e)})
        return False, None, f"Twilio: {e.msg or str(e)}"
    except Exception as e:  # pragma: no cover
        logger.exception("sms_error")
        return False, None, str(e)


class SmsService:
    """Wrapper de compatibilidad para el router /notify/sms."""

    def send(self, to: str, body: str) -> str:
        ok, sid, err = send_sms(to, body)
        if not ok:
            raise RuntimeError(err or "SMS falló")
        return sid or ""


def _track_url(public_base_url: str, tracking_code: str) -> str:
    base = (public_base_url or "").rstrip("/")
    return f"{base}/track/{tracking_code}" if base else f"/track/{tracking_code}"


def build_shipment_sms(
    *,
    public_base_url: str,
    order_code: Optional[str],
    tracking_code: str,
    carrier: str,
    weight_kg: Optional[float],
    estimated_delivery: Optional[str],
    destination: str,
    photo_urls: List[str],
) -> str:
    lines = ["HECORP • Envío"]
    if order_code:
        lines.append(f"Pedido: {order_code}")
    lines.append(f"Guía: {tracking_code}")
    lines.append(f"Paquetería: {carrier}")
    if weight_kg is not None:
        lines.append(f"Peso: {weight_kg} kg")
    if estimated_delivery:
        lines.append(f"Entrega estimada: {estimated_delivery}")
    lines.append(f"Destino: {destination}")
    lines.append(f"Rastrea: {_track_url(public_base_url, tracking_code)}")
    if photo_urls:
        base = public_base_url.rstrip("/")
        for i, u in enumerate(photo_urls[:3], 1):
            full = u if u.startswith("http") else f"{base}{u}"
            lines.append(f"Foto {i}: {full}")
    return "\n".join(lines)
