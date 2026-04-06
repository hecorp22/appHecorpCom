# app/routers/bot.py
from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from app.core.config import settings
from app.routers.auth_router import get_current_user_from_cookie
from app.database import get_db

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


# ===== MODELO PARA EL BODY DEL POST =====

class TelegramPayload(BaseModel):
    title: str
    comment: str
    link: str | None = None


# ===== PÁGINA /bot =====

@router.get("/bot")
def bot_page(
    request: Request,
    user: str = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Página principal para enviar mensajes e imágenes al VPS / Telegram
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "vps_url": settings.VPS_URL,   # lo puedes seguir usando si quieres
            "eventos": [],                 # para que tu template no truene
        }
    )


# ===== FUNCIONES AUXILIARES PARA TELEGRAM =====

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_telegram_text(chat_id: int, text: str) -> dict:
    """
    Envía un mensaje de texto a Telegram usando la Bot API.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{TELEGRAM_API_BASE}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": False,
                "parse_mode": "HTML",
            },
        )
    if resp.status_code != 200:
        # Log para depuración
        print("ERROR TELEGRAM:", resp.status_code, resp.text)
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar a Telegram: {resp.text}",
        )
    return resp.json()


def build_message(payload: TelegramPayload) -> str:
    """
    Construye el mensaje que se enviará a Telegram usando title/comment/link.
    """
    parts = []

    if payload.title:
        parts.append(f"<b>{payload.title}</b>")

    if payload.comment:
        parts.append(payload.comment.strip())

    if payload.link:
        parts.append(f"\n🔗 {payload.link}")

    return "\n\n".join(parts).strip() or "Mensaje vacío"


# ===== ENDPOINT API /api/telegram/send/{target} =====

@router.post("/api/telegram/send/{target}")
async def send_telegram_message(
    target: str,
    payload: TelegramPayload,
    user: str = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    """
    Recibe title, comment, link y los envía al bot O al grupo según {target}.
    """
    if target not in ("bot", "group"):
        raise HTTPException(status_code=404, detail="Destino no soportado")

    text = build_message(payload)

    if target == "bot":
        chat_id = settings.TELEGRAM_BOT_CHAT_ID
    else:  # "group"
        chat_id = settings.TELEGRAM_GROUP_CHAT_ID

    telegram_resp = await send_telegram_text(chat_id=chat_id, text=text)

    return {
        "ok": telegram_resp.get("ok", False),
        "target": target,
        "sent_to": chat_id,
        "payload": payload,
        "telegram_response": telegram_resp,
    }