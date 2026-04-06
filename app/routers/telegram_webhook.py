# app/routers/telegram_webhook.py (puedes meterlo también en bot.py si quieres)

from fastapi import APIRouter
from app.core.config import settings
import httpx

router = APIRouter()

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

async def telegram_send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API_BASE}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
        )

@router.post("/api/telegram/webhook")
async def telegram_webhook(update: dict):
    """
    Webhook que recibe TODOS los eventos del bot.
    Telegram envía un JSON tipo:
    {
      "update_id": ...,
      "message": {
          "chat": { "id": ... },
          "from": { ... },
          "text": "..."
      }
    }
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}  # ignoramos otros tipos (callback_query, etc.)

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "") or ""

    # Ejemplo simple: si alguien escribe /ping, respondemos "pong"
    if text.startswith("/ping"):
        await telegram_send_message(chat_id, "pong 🏓")

    # Ejemplo: si alguien escribe "hola", contestamos algo
    elif "hola" in text.lower():
        await telegram_send_message(chat_id, "Hola desde NOX_hecorp_bot 👾")

    # Puedes agregar más lógica aquí (responder solo en cierto grupo, comandos, etc.)
    return {"ok": True}