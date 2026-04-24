"""
Router de ENTREGAS (delivery) — separado de Shipments de Aleaciones.
Monta /delivery (HTML admin + tracking público) y /api/delivery (JSON).
"""
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, HTTPException, Query, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth_router import get_current_user_from_cookie
from app.schemas.delivery_schema import (
    DriverIn, DriverOut,
    DeliveryCustomerIn, DeliveryCustomerOut,
    DeliveryIn, DeliveryOut,
    DeliveryRunIn, DeliveryRunOut,
)
from app.services import delivery_service as svc

templates = Jinja2Templates(directory="app/templates")

# ------------------ HTML ------------------
html = APIRouter(tags=["delivery-html"])


@html.get("/delivery", response_class=HTMLResponse)
def delivery_dashboard(request: Request,
                       user: str = Depends(get_current_user_from_cookie),
                       db: Session = Depends(get_db)):
    kpi = svc.kpi_today(db)
    return templates.TemplateResponse(
        "delivery_admin.html",
        {"request": request, "user": user, "kpi": kpi},
    )


@html.get("/track/d/{code}", response_class=HTMLResponse)
def public_track_delivery(code: str, request: Request, db: Session = Depends(get_db)):
    d = db.query(svc.Delivery).filter_by(code=code.strip()).first()
    if not d:
        raise HTTPException(404, "Entrega no encontrada")
    return templates.TemplateResponse(
        "delivery_track_public.html",
        {"request": request, "d": d, "cust": d.customer, "drv": d.driver},
    )


# ------------------ API ------------------
api = APIRouter(prefix="/api/delivery", tags=["delivery-api"])


# ---- drivers ----
@api.get("/drivers", response_model=list[DriverOut])
def api_drivers(active: Optional[int] = None,
                db: Session = Depends(get_db),
                _=Depends(get_current_user_from_cookie)):
    return svc.list_drivers(db, active=active)


@api.post("/drivers", response_model=DriverOut)
def api_driver_create(payload: DriverIn,
                      db: Session = Depends(get_db),
                      _=Depends(get_current_user_from_cookie)):
    return svc.create_driver(db, payload.model_dump())


@api.patch("/drivers/{did}", response_model=DriverOut)
def api_driver_update(did: int, payload: DriverIn,
                      db: Session = Depends(get_db),
                      _=Depends(get_current_user_from_cookie)):
    return svc.update_driver(db, did, payload.model_dump(exclude_unset=True))


@api.delete("/drivers/{did}")
def api_driver_delete(did: int,
                      db: Session = Depends(get_db),
                      _=Depends(get_current_user_from_cookie)):
    svc.delete_driver(db, did)
    return {"ok": True}


# ---- customers ----
@api.get("/customers", response_model=list[DeliveryCustomerOut])
def api_customers(q: str = "", kind: Optional[str] = None,
                  db: Session = Depends(get_db),
                  _=Depends(get_current_user_from_cookie)):
    return svc.list_customers(db, q=q, kind=kind)


@api.post("/customers", response_model=DeliveryCustomerOut)
def api_customer_create(payload: DeliveryCustomerIn,
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    return svc.create_customer(db, payload.model_dump())


@api.patch("/customers/{cid}", response_model=DeliveryCustomerOut)
def api_customer_update(cid: int, payload: DeliveryCustomerIn,
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    return svc.update_customer(db, cid, payload.model_dump(exclude_unset=True))


@api.delete("/customers/{cid}")
def api_customer_delete(cid: int,
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    svc.delete_customer(db, cid)
    return {"ok": True}


# ---- runs ----
@api.get("/runs", response_model=list[DeliveryRunOut])
def api_runs(date_from: Optional[datetime] = None,
             date_to: Optional[datetime] = None,
             status: Optional[str] = None,
             db: Session = Depends(get_db),
             _=Depends(get_current_user_from_cookie)):
    return svc.list_runs(db, date_from=date_from, date_to=date_to, status=status)


@api.get("/runs/{run_id}", response_model=DeliveryRunOut)
def api_run_get(run_id: int,
                db: Session = Depends(get_db),
                _=Depends(get_current_user_from_cookie)):
    return svc.get_run(db, run_id)


@api.post("/runs", response_model=DeliveryRunOut)
def api_run_create(payload: DeliveryRunIn,
                   db: Session = Depends(get_db),
                   _=Depends(get_current_user_from_cookie)):
    return svc.create_run(db, payload.model_dump())


@api.patch("/runs/{run_id}/status", response_model=DeliveryRunOut)
def api_run_status(run_id: int,
                   status: str = Body(..., embed=True),
                   db: Session = Depends(get_db),
                   _=Depends(get_current_user_from_cookie)):
    return svc.update_run_status(db, run_id, status)


@api.delete("/runs/{run_id}")
def api_run_delete(run_id: int,
                   db: Session = Depends(get_db),
                   _=Depends(get_current_user_from_cookie)):
    svc.delete_run(db, run_id)
    return {"ok": True}


# ---- deliveries ----
@api.get("", response_model=list[DeliveryOut])
def api_deliveries(run_id: Optional[int] = None,
                   driver_id: Optional[int] = None,
                   status: Optional[str] = None,
                   late_only: bool = False,
                   db: Session = Depends(get_db),
                   _=Depends(get_current_user_from_cookie)):
    return svc.list_deliveries(db, run_id=run_id, driver_id=driver_id,
                               status=status, late_only=late_only)


@api.get("/{did}", response_model=DeliveryOut)
def api_delivery_get(did: int,
                     db: Session = Depends(get_db),
                     _=Depends(get_current_user_from_cookie)):
    return svc.get_delivery(db, did)


@api.post("", response_model=DeliveryOut)
def api_delivery_create(payload: DeliveryIn,
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    return svc.create_delivery(db, payload.model_dump())


@api.patch("/{did}", response_model=DeliveryOut)
def api_delivery_update(did: int, payload: DeliveryIn,
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    return svc.update_delivery(db, did, payload.model_dump(exclude_unset=True))


@api.patch("/{did}/status", response_model=DeliveryOut)
def api_delivery_status(did: int,
                        status: str = Body(..., embed=True),
                        message: Optional[str] = Body(None, embed=True),
                        report: Optional[str] = Body(None, embed=True),
                        issue_code: Optional[str] = Body(None, embed=True),
                        issue_detail: Optional[str] = Body(None, embed=True),
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    return svc.change_delivery_status(db, did, status,
                                      message=message, report=report,
                                      issue_code=issue_code, issue_detail=issue_detail)


@api.delete("/{did}")
def api_delivery_delete(did: int,
                        db: Session = Depends(get_db),
                        _=Depends(get_current_user_from_cookie)):
    svc.delete_delivery(db, did)
    return {"ok": True}


# ---- kpi ----
@api.get("/kpi/today")
def api_kpi_today(db: Session = Depends(get_db),
                  _=Depends(get_current_user_from_cookie)):
    return svc.kpi_today(db)
