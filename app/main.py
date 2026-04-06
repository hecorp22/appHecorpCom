from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth_router, home_router, decriptData_router, bot, agenda,maps,rutas_router,telegram_webhook,payroll_router,user_admin_router

# NUEVO: logs + métricas
from app.core.logging_conf import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.metrics import instrument, CustomLatencyMiddleware
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
# CORS (usas cookies → allow_credentials=True y orígenes explícitos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type","X-Requested-With","X-CSRF-Token"],
    expose_headers=["X-Trace-Id"],
)

# Logging JSON
logger = setup_logging()

# Middlewares
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CustomLatencyMiddleware)

# Health
@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}

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
app.include_router(cfdi_router.router)
app.include_router(telegram_webhook.router)
app.include_router(face_router.router)
app.include_router(public_router.router)
app.include_router(term_router.router)
app.include_router(payroll_router.router)
app.include_router(user_admin_router.router)


# Templates / estáticos
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Prometheus
instrument(app)
