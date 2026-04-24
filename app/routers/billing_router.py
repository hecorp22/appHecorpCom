"""Router de cobranza."""
import os
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, HTTPException, Body, Header, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth_router import get_current_user_from_cookie
from app.schemas.billing_schema import (
    InvoiceIn, InvoiceOut, PaymentIn, PaymentOut, InvoiceFromDelivery,
)
from app.services import billing_service as svc

templates = Jinja2Templates(directory="app/templates")

# ------------------ HTML ------------------
html = APIRouter(tags=["billing-html"])


@html.get("/billing", response_class=HTMLResponse)
def billing_dashboard(request: Request,
                      user: str = Depends(get_current_user_from_cookie),
                      db: Session = Depends(get_db)):
    kpi = svc.kpi_billing(db)
    return templates.TemplateResponse(
        "billing_admin.html",
        {"request": request, "user": user, "kpi": kpi},
    )


# ------------------ API ------------------
api = APIRouter(prefix="/api/billing", tags=["billing-api"])


@api.get("/invoices", response_model=List[InvoiceOut])
def api_list(status: Optional[str] = None, q: str = "",
             overdue_only: bool = False, limit: int = 200,
             db: Session = Depends(get_db),
             _=Depends(get_current_user_from_cookie)):
    # las propiedades balance y days_overdue del modelo Invoice se serializan solas
    return svc.list_invoices(db, status=status, q=q,
                              overdue_only=overdue_only, limit=limit)


@api.get("/invoices/{iid}", response_model=InvoiceOut)
def api_get(iid: int,
            db: Session = Depends(get_db),
            _=Depends(get_current_user_from_cookie)):
    return svc.get_invoice(db, iid)


@api.post("/invoices", response_model=InvoiceOut)
def api_create(payload: InvoiceIn,
               db: Session = Depends(get_db),
               _=Depends(get_current_user_from_cookie)):
    return svc.create_invoice(db, payload.model_dump())


@api.post("/invoices/from-delivery", response_model=InvoiceOut)
def api_from_delivery(payload: InvoiceFromDelivery,
                      db: Session = Depends(get_db),
                      _=Depends(get_current_user_from_cookie)):
    return svc.from_delivery(
        db, payload.delivery_id,
        due_days=payload.due_days, tax_pct=payload.tax_pct,
        notes=payload.notes,
    )


@api.post("/invoices/{iid}/cancel", response_model=InvoiceOut)
def api_cancel(iid: int,
               db: Session = Depends(get_db),
               _=Depends(get_current_user_from_cookie)):
    return svc.cancel_invoice(db, iid)


# ---- pagos ----
@api.post("/invoices/{iid}/payments", response_model=PaymentOut)
def api_pay(iid: int, payload: PaymentIn,
            db: Session = Depends(get_db),
            user=Depends(get_current_user_from_cookie)):
    user_email = getattr(user, "email", None) or (user if isinstance(user, str) else None)
    return svc.add_payment(db, iid, payload.model_dump(), user_email=user_email)


@api.delete("/payments/{pid}")
def api_pay_delete(pid: int,
                   db: Session = Depends(get_db),
                   _=Depends(get_current_user_from_cookie)):
    svc.delete_payment(db, pid)
    return {"ok": True}


# ---- KPIs ----
@api.get("/kpi")
def api_kpi(db: Session = Depends(get_db),
            _=Depends(get_current_user_from_cookie)):
    return svc.kpi_billing(db)


# ---- Cron de recordatorios ----
@api.post("/cron/reminders")
def api_cron_reminders(x_cron_token: Optional[str] = Header(None),
                       db: Session = Depends(get_db)):
    expected = os.getenv("CRON_TOKEN")
    if not expected or x_cron_token != expected:
        raise HTTPException(401, "Cron token inválido")
    return svc.run_reminders(db)
