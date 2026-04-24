"""
Email service — usa Resend (https://resend.com) si RESEND_API_KEY está configurada.
Tolerante a fallos: si no está configurado o falla, retorna (ok=False, error=...).

Variables de entorno esperadas:
  RESEND_API_KEY     API key de Resend
  EMAIL_FROM         remitente, ej. "Aleaciones y Maquinados <ventas@aleacionesymaquinados.mx>"
  EMAIL_REPLY_TO     (opcional) dirección de respuesta
"""
import os
import base64
import logging
from typing import Optional, Tuple, List, Dict, Any

import requests

logger = logging.getLogger("app.email")

RESEND_API_URL = "https://api.resend.com/emails"


def _cfg() -> Tuple[str, str, Optional[str]]:
    key = os.getenv("RESEND_API_KEY", "").strip()
    frm = os.getenv("EMAIL_FROM", "").strip()
    rep = os.getenv("EMAIL_REPLY_TO", "").strip() or None
    return key, frm, rep


def send_email(
    to: str | List[str],
    subject: str,
    html: Optional[str] = None,
    text: Optional[str] = None,
    *,
    attachments: Optional[List[Dict[str, Any]]] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Retorna (ok, message_id|None, error|None).

    attachments: [{"filename": "cot.pdf", "content": bytes, "content_type": "application/pdf"}, ...]
    """
    key, frm, reply_to = _cfg()
    if not key:
        return False, None, "Resend no configurado (falta RESEND_API_KEY en .env)"
    if not frm:
        return False, None, "Remitente no configurado (falta EMAIL_FROM en .env)"

    if isinstance(to, str):
        to_list = [to]
    else:
        to_list = list(to)
    to_list = [t.strip() for t in to_list if t and t.strip()]
    if not to_list:
        return False, None, "Destinatario vacío"

    payload: Dict[str, Any] = {
        "from": frm,
        "to": to_list,
        "subject": subject[:200],
    }
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc
    if attachments:
        payload["attachments"] = [
            {
                "filename": a["filename"],
                "content": base64.b64encode(a["content"]).decode("ascii"),
                "content_type": a.get("content_type", "application/octet-stream"),
            }
            for a in attachments
        ]

    try:
        r = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=20,
        )
        if r.status_code >= 400:
            try:
                err = r.json().get("message") or r.text
            except Exception:
                err = r.text
            logger.error("email_resend_error", extra={"status": r.status_code, "error": err})
            return False, None, f"Resend {r.status_code}: {err}"
        data = r.json() if r.content else {}
        mid = data.get("id")
        logger.info("email_sent", extra={"to": to_list, "id": mid})
        return True, mid, None
    except requests.RequestException as e:
        logger.exception("email_exception")
        return False, None, f"HTTP error: {e}"
    except Exception as e:  # pragma: no cover
        logger.exception("email_unexpected")
        return False, None, str(e)
