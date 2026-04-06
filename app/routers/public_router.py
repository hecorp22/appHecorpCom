from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# 👇 ESTO TE FALTABA EN ESE ARCHIVO
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})
