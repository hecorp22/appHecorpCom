from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
import os

from app.routers.auth_router import get_current_user_from_cookie

router = APIRouter()

PAGE_ID = os.getenv("PAGE_ID")
PAGE_TOKEN = os.getenv("PAGE_TOKEN")


class FacebookPayload(BaseModel):
    title: str | None = None
    comment: str
    link: str | None = None
    image_url: str | None = None   # 👈 nuevo campo


@router.post("/api/facebook/post")
async def post_facebook(
    payload: FacebookPayload,
    user: str = Depends(get_current_user_from_cookie),
):
    if not PAGE_ID or not PAGE_TOKEN:
        raise HTTPException(status_code=500, detail="Faltan variables de entorno")

    message = f"{payload.title or ''}\n\n{payload.comment}"

    if payload.link:
        message += f"\n\n🔗 {payload.link}"

    async with httpx.AsyncClient(timeout=15) as client:

        # 🔥 POST CON IMAGEN
        if payload.image_url:
            url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
            data = {
                "url": payload.image_url,
                "caption": message,
                "access_token": PAGE_TOKEN
            }

        # 📝 SOLO TEXTO
        else:
            url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
            data = {
                "message": message,
                "access_token": PAGE_TOKEN
            }

        resp = await client.post(url, data=data)

    if resp.status_code != 200:
        print("ERROR FACEBOOK:", resp.status_code, resp.text)
        raise HTTPException(status_code=500, detail=resp.text)

    return resp.json()