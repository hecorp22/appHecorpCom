import json
from pathlib import Path
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.auth_deps import require_admin
from app.models.user_model import User

router = APIRouter(tags=["observability"])
templates = Jinja2Templates(directory="app/templates")

LOG_FILE = Path("logs/app.json.log")


def _tail_lines(path: Path, n: int) -> list[str]:
    if not path.exists():
        return []
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            block = 4096
            data = b""
            while size > 0 and data.count(b"\n") <= n:
                step = min(block, size)
                size -= step
                f.seek(size)
                data = f.read(step) + data
            lines = data.splitlines()[-n:]
            return [ln.decode("utf-8", errors="replace") for ln in lines]
    except Exception:
        return []


@router.get("/admin/observability", response_class=HTMLResponse)
def observability_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "observability.html",
        {"request": request, "user": user},
    )


@router.get("/admin/logs.json")
def logs_json(
    n: int = Query(200, ge=1, le=2000),
    level: str | None = None,
    method: str | None = None,
    path: str | None = None,
    _: User = Depends(require_admin),
):
    lines = _tail_lines(LOG_FILE, n)
    entries = []
    for raw in lines:
        try:
            obj = json.loads(raw)
        except Exception:
            entries.append({"raw": raw})
            continue

        rec = obj.get("record") or obj
        extra = rec.get("extra") or {}
        entry = {
            "time": (rec.get("time") or {}).get("repr"),
            "level": (rec.get("level") or {}).get("name"),
            "message": rec.get("message") or obj.get("text", "").strip(),
            "module": rec.get("module"),
            "method": extra.get("method"),
            "path": extra.get("path"),
            "status": extra.get("status"),
            "duration_ms": extra.get("duration_ms"),
            "trace_id": extra.get("trace_id"),
            "error": extra.get("error"),
            "user": extra.get("user"),
        }
        if level and entry.get("level") != level.upper():
            continue
        if method and entry.get("method") != method.upper():
            continue
        if path and path not in (entry.get("path") or ""):
            continue
        entries.append(entry)
    return {"count": len(entries), "entries": list(reversed(entries))}  # recientes primero
