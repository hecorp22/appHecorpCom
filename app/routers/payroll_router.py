import csv
from pathlib import Path
from typing import List, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from app.routers.auth_router import get_current_user_from_cookie
from app.settings import settings

router = APIRouter(prefix="/nomina", tags=["nomina"])
templates = Jinja2Templates(directory="app/templates")

DATA_FILE = Path(__file__).resolve().parents[1] / "static" / "empleados_nomina.csv"


def _read_csv() -> List[Dict[str, str]]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


@router.get("/")
def payroll_dashboard(
    request: Request, user: str = Depends(get_current_user_from_cookie)
):
    registros = _read_csv()
    total_nomina = sum(float(row.get("Total_Pagar_MXN", 0)) for row in registros)
    return templates.TemplateResponse(
        "nomina.html",
        {
            "request": request,
            "user": user,
            "registros": registros,
            "total_nomina": total_nomina,
            "archivo": DATA_FILE.name,
            "download_url": f"{settings.VPS_URL.rstrip('/')}/nomina/download",
        },
    )


@router.get("/download")
def download_payroll(user: str = Depends(get_current_user_from_cookie)):
    if not DATA_FILE.exists():
        raise FileNotFoundError("No se encontró el archivo de nómina")
    return FileResponse(
        path=DATA_FILE,
        media_type="text/csv",
        filename=DATA_FILE.name,
    )
