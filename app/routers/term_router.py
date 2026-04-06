from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# 👇 ESTO TE FALTABA EN ESE ARCHIVO
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})