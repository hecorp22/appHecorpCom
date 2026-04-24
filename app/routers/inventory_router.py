"""Router de Inventario."""
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, HTTPException, Body, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth_router import get_current_user_from_cookie
from app.schemas.inventory_schema import (
    WarehouseIn, WarehouseOut,
    ProductIn, ProductOut,
    MovementIn, MovementOut,
    TransferIn,
    StockOut,
    DeliveryItemIn, DeliveryItemOut,
)
from app.services import inventory_service as svc

templates = Jinja2Templates(directory="app/templates")

# ------------------ HTML ------------------
html = APIRouter(tags=["inventory-html"])


@html.get("/inventory", response_class=HTMLResponse)
def inventory_dashboard(request: Request,
                        user: str = Depends(get_current_user_from_cookie),
                        db: Session = Depends(get_db)):
    kpi = svc.kpi_inventory(db)
    return templates.TemplateResponse(
        "inventory_admin.html",
        {"request": request, "user": user, "kpi": kpi},
    )


# ------------------ API ------------------
api = APIRouter(prefix="/api/inventory", tags=["inventory-api"])


# ---- warehouses ----
@api.get("/warehouses", response_model=List[WarehouseOut])
def api_wh_list(active: Optional[int] = None,
                db: Session = Depends(get_db),
                _=Depends(get_current_user_from_cookie)):
    return svc.list_warehouses(db, active=active)


@api.post("/warehouses", response_model=WarehouseOut)
def api_wh_create(payload: WarehouseIn,
                  db: Session = Depends(get_db),
                  _=Depends(get_current_user_from_cookie)):
    return svc.create_warehouse(db, payload.model_dump())


@api.patch("/warehouses/{wid}", response_model=WarehouseOut)
def api_wh_update(wid: int, payload: WarehouseIn,
                  db: Session = Depends(get_db),
                  _=Depends(get_current_user_from_cookie)):
    return svc.update_warehouse(db, wid, payload.model_dump(exclude_unset=True))


# ---- products ----
@api.get("/products", response_model=List[ProductOut])
def api_p_list(q: str = "", category: Optional[str] = None,
               low_only: bool = False, active: Optional[int] = None,
               db: Session = Depends(get_db),
               _=Depends(get_current_user_from_cookie)):
    return svc.list_products(db, q=q, category=category, low_only=low_only, active=active)


@api.get("/products/{pid}", response_model=ProductOut)
def api_p_get(pid: int,
              db: Session = Depends(get_db),
              _=Depends(get_current_user_from_cookie)):
    return svc.get_product(db, pid)


@api.post("/products", response_model=ProductOut)
def api_p_create(payload: ProductIn,
                 db: Session = Depends(get_db),
                 _=Depends(get_current_user_from_cookie)):
    return svc.create_product(db, payload.model_dump())


@api.patch("/products/{pid}", response_model=ProductOut)
def api_p_update(pid: int, payload: ProductIn,
                 db: Session = Depends(get_db),
                 _=Depends(get_current_user_from_cookie)):
    return svc.update_product(db, pid, payload.model_dump(exclude_unset=True))


@api.delete("/products/{pid}")
def api_p_delete(pid: int,
                 db: Session = Depends(get_db),
                 _=Depends(get_current_user_from_cookie)):
    svc.delete_product(db, pid)
    return {"ok": True}


# ---- movements ----
@api.post("/movements", response_model=MovementOut)
def api_mov_create(payload: MovementIn,
                   db: Session = Depends(get_db),
                   user=Depends(get_current_user_from_cookie)):
    user_email = getattr(user, "email", None) or (user if isinstance(user, str) else None)
    return svc.apply_movement(
        db,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        kind=payload.kind,
        qty=payload.qty,
        reason=payload.reason,
        reference=payload.reference,
        user_email=user_email,
    )


@api.get("/movements", response_model=List[MovementOut])
def api_mov_list(product_id: Optional[int] = None,
                 warehouse_id: Optional[int] = None,
                 limit: int = 200,
                 db: Session = Depends(get_db),
                 _=Depends(get_current_user_from_cookie)):
    return svc.list_movements(db, product_id=product_id,
                              warehouse_id=warehouse_id, limit=limit)


@api.post("/transfer")
def api_transfer(payload: TransferIn,
                 db: Session = Depends(get_db),
                 user=Depends(get_current_user_from_cookie)):
    user_email = getattr(user, "email", None) or (user if isinstance(user, str) else None)
    res = svc.transfer(db,
        product_id=payload.product_id,
        from_wh=payload.from_wh, to_wh=payload.to_wh,
        qty=payload.qty, reason=payload.reason, user_email=user_email)
    return {"ok": True, "out_id": res["out"].id, "in_id": res["in"].id}


# ---- stocks ----
@api.get("/stocks", response_model=List[StockOut])
def api_stocks(warehouse_id: Optional[int] = None,
               db: Session = Depends(get_db),
               _=Depends(get_current_user_from_cookie)):
    return svc.list_stock(db, warehouse_id=warehouse_id)


# ---- delivery items ----
@api.post("/deliveries/{did}/items", response_model=DeliveryItemOut)
def api_di_add(did: int, payload: DeliveryItemIn,
               db: Session = Depends(get_db),
               _=Depends(get_current_user_from_cookie)):
    return svc.attach_delivery_item(
        db, did, payload.product_id, payload.qty,
        price=payload.price, note=payload.note)


@api.get("/deliveries/{did}/items", response_model=List[DeliveryItemOut])
def api_di_list(did: int,
                db: Session = Depends(get_db),
                _=Depends(get_current_user_from_cookie)):
    return svc.list_delivery_items(db, did)


# ---- KPIs ----
@api.get("/kpi")
def api_kpi(db: Session = Depends(get_db),
            _=Depends(get_current_user_from_cookie)):
    return svc.kpi_inventory(db)
