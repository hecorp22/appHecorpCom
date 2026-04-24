from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import (
    auth_router,
    home_router,
    decriptData_router,
    bot,
    agenda,
    maps,
    rutas_router,
    telegram_webhook,
    payroll_router,
    user_admin_router,
    client_router,
    provider_router,
    provider_account_router,
    order_router,
    shipment_router,
    observability_router,
    tracking_router,
    kpi_router,
    export_router,
    quotation_router,
)
from app.models import quotation as _m_quote  # noqa: F401

# Registrar modelos nuevos para que Base.metadata.create_all los cree
from app.models import provider_account as _m_pa  # noqa: F401
from app.models import order as _m_order           # noqa: F401
from app.models import shipment as _m_shipment     # noqa: F401
from app.models import delivery as _m_delivery     # noqa: F401
from app.models import inventory as _m_inventory   # noqa: F401

# NUEVO: logs + métricas
from app.core.logging_conf import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.metrics import instrument, CustomLatencyMiddleware
from app.core.auth_deps import require_admin
from app.models.user_model import User
from app.routers import notify_router
from app.routers import cfdi_router
from app.routers import face_router
from app.routers import public_router
from app.routers import term_router


# ALLOWED_ORIGINS desde settings/.env (opcional)
try:
    from app.settings import settings
    ALLOWED_ORIGINS = [o.strip() for o in getattr(settings, "ALLOWED_ORIGINS", "").split(",") if o.strip()]
except Exception:
    ALLOWED_ORIGINS = [
        "https://hecorp.com.mx",
        "https://www.hecorp.com.mx",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app = FastAPI(
    title="HECORP APPS",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# CORS (usas cookies → allow_credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-CSRF-Token"],
    expose_headers=["X-Trace-Id"],
)

# Logging JSON
logger = setup_logging()

# Middlewares
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CustomLatencyMiddleware)

# Templates / estáticos (ANTES de las rutas que los usan)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Health
@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}


# --- Assets públicos básicos ---
@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    return FileResponse("app/static/favicon.svg", media_type="image/svg+xml")


@app.get("/favicon.png", include_in_schema=False)
def favicon_png():
    return FileResponse("app/static/favicon.svg", media_type="image/svg+xml")


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    return FileResponse("app/static/robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>https://hecorp.com.mx/</loc></url>'
        '<url><loc>https://hecorp.com.mx/login</loc></url>'
        '</urlset>'
    )
    return Response(content=body, media_type="application/xml")


@app.get("/.well-known/security.txt", include_in_schema=False)
def security_txt():
    body = (
        "Contact: mailto:seguridad@aleacionesymaquinados.mx\n"
        "Preferred-Languages: es, en\n"
        "Canonical: https://hecorp.com.mx/.well-known/security.txt\n"
    )
    return PlainTextResponse(body)


# DB (ya apuntas a tu VPS con sslmode=require)
Base.metadata.create_all(bind=engine)


# Routers
app.include_router(auth_router.router)
app.include_router(home_router.router)
app.include_router(decriptData_router.router)
app.include_router(bot.router)
app.include_router(agenda.router)
app.include_router(notify_router.router)
app.include_router(maps.router)
app.include_router(rutas_router.router)
app.include_router(rutas_router.api)
# Módulo Delivery (víveres/tortillas/paquetes)
from app.routers import delivery_router  # noqa: E402
app.include_router(delivery_router.html)
app.include_router(delivery_router.api)
# Módulo Inventario
from app.routers import inventory_router  # noqa: E402
app.include_router(inventory_router.html)
app.include_router(inventory_router.api)
app.include_router(cfdi_router.router)
app.include_router(telegram_webhook.router)
app.include_router(face_router.router)
app.include_router(public_router.router)
app.include_router(term_router.router)
app.include_router(payroll_router.router)
app.include_router(user_admin_router.router)
app.include_router(client_router.router)
app.include_router(provider_router.router)
app.include_router(provider_account_router.router)
app.include_router(order_router.router)
app.include_router(shipment_router.router)
app.include_router(observability_router.router)
app.include_router(tracking_router.router)
app.include_router(kpi_router.router)
app.include_router(export_router.router)
app.include_router(quotation_router.router)


# Provider Administration View (solo admin/superuser)
@app.get('/admin/providers', response_class=HTMLResponse)
def provider_admin_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "provider_admin.html",
        {"request": request, "user": user}
    )


# Client Administration View (solo admin/superuser)
@app.get('/admin/clients', response_class=HTMLResponse)
def client_admin_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "client_admin.html",
        {"request": request, "user": user}
    )


# Admin dashboard
@app.get('/admin/dashboard', response_class=HTMLResponse)
def admin_dashboard(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user}
    )


# Quotations admin view
@app.get('/admin/quotations', response_class=HTMLResponse)
def quotations_admin_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "quotations_admin.html",
        {"request": request, "user": user}
    )


# Orders admin view
@app.get('/admin/orders', response_class=HTMLResponse)
def orders_admin_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "orders_admin.html",
        {"request": request, "user": user}
    )


# Shipments admin view
@app.get('/admin/shipments', response_class=HTMLResponse)
def shipments_admin_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(
        "shipments_admin.html",
        {"request": request, "user": user}
    )


# Prometheus
instrument(app)
