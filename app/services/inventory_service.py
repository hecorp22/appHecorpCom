"""
Servicio de inventario.
Lógica de stock con validación, registro de movimiento y alertas de reorden.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.inventory import (
    Product, Warehouse, Stock, StockMovement, DeliveryItem,
)
from app.services.admin_notify import _send as admin_send

ZERO = Decimal("0")


# --------------------------------------------------------------------------- #
# Warehouse
# --------------------------------------------------------------------------- #
def list_warehouses(db: Session, active: Optional[int] = None) -> List[Warehouse]:
    q = db.query(Warehouse)
    if active is not None:
        q = q.filter(Warehouse.active == active)
    return q.order_by(Warehouse.name).all()


def get_default_warehouse(db: Session) -> Warehouse:
    w = db.query(Warehouse).filter_by(is_default=1, active=1).first()
    if w:
        return w
    w = db.query(Warehouse).filter_by(active=1).first()
    if not w:
        # crear default si no hay ninguno
        w = Warehouse(code="MAIN", name="Almacén principal", is_default=1, active=1)
        db.add(w); db.commit(); db.refresh(w)
    return w


def create_warehouse(db: Session, data: Dict[str, Any]) -> Warehouse:
    if data.get("is_default"):
        # solo uno default
        db.query(Warehouse).update({Warehouse.is_default: 0})
    w = Warehouse(**data)
    db.add(w); db.commit(); db.refresh(w)
    return w


def update_warehouse(db: Session, wid: int, data: Dict[str, Any]) -> Warehouse:
    w = db.query(Warehouse).filter_by(id=wid).first()
    if not w:
        raise HTTPException(404, "Almacén no encontrado")
    if data.get("is_default"):
        db.query(Warehouse).filter(Warehouse.id != wid).update({Warehouse.is_default: 0})
    for k, v in data.items():
        setattr(w, k, v)
    db.commit(); db.refresh(w)
    return w


# --------------------------------------------------------------------------- #
# Product
# --------------------------------------------------------------------------- #
def _decorate(db: Session, p: Product) -> Product:
    total = (db.query(func.coalesce(func.sum(Stock.qty), 0))
             .filter(Stock.product_id == p.id).scalar() or ZERO)
    p.total_qty = Decimal(total)
    p.low_stock = bool(p.stock_min and Decimal(total) <= Decimal(p.stock_min))
    return p


def list_products(db: Session, q: str = "", category: Optional[str] = None,
                  low_only: bool = False, active: Optional[int] = None) -> List[Product]:
    query = db.query(Product)
    if q:
        ilike = f"%{q}%"
        query = query.filter(
            (Product.name.ilike(ilike)) | (Product.sku.ilike(ilike))
        )
    if category:
        query = query.filter(Product.category == category)
    if active is not None:
        query = query.filter(Product.active == active)
    items = query.order_by(Product.name).limit(500).all()
    out = [_decorate(db, p) for p in items]
    if low_only:
        out = [p for p in out if p.low_stock]
    return out


def get_product(db: Session, pid: int) -> Product:
    p = db.query(Product).filter_by(id=pid).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    return _decorate(db, p)


def create_product(db: Session, data: Dict[str, Any]) -> Product:
    if db.query(Product).filter_by(sku=data["sku"]).first():
        raise HTTPException(400, f"SKU '{data['sku']}' ya existe")
    p = Product(**data)
    db.add(p); db.commit(); db.refresh(p)
    return _decorate(db, p)


def update_product(db: Session, pid: int, data: Dict[str, Any]) -> Product:
    p = db.query(Product).filter_by(id=pid).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    for k, v in data.items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return _decorate(db, p)


def delete_product(db: Session, pid: int) -> None:
    p = db.query(Product).filter_by(id=pid).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    db.delete(p); db.commit()


# --------------------------------------------------------------------------- #
# Stock helpers (núcleo)
# --------------------------------------------------------------------------- #
def _get_or_create_stock(db: Session, product_id: int, warehouse_id: int) -> Stock:
    s = (db.query(Stock)
         .filter_by(product_id=product_id, warehouse_id=warehouse_id).first())
    if not s:
        s = Stock(product_id=product_id, warehouse_id=warehouse_id, qty=ZERO)
        db.add(s); db.flush()
    return s


def apply_movement(db: Session, *,
                   product_id: int, warehouse_id: int,
                   kind: str, qty: Decimal,
                   reason: Optional[str] = None,
                   reference: Optional[str] = None,
                   user_email: Optional[str] = None) -> StockMovement:
    """
    Aplica un movimiento de stock con validación.
    Reglas:
      - entrada: suma
      - salida: resta (no permite quedar < 0)
      - ajuste: setea qty exacta (qty es la cantidad nueva, no delta)
    """
    if qty is None:
        raise HTTPException(400, "qty requerido")
    qty = Decimal(qty)
    if qty < 0:
        raise HTTPException(400, "qty no puede ser negativo")

    p = db.query(Product).filter_by(id=product_id).first()
    if not p:
        raise HTTPException(400, "Producto no existe")
    w = db.query(Warehouse).filter_by(id=warehouse_id).first()
    if not w:
        raise HTTPException(400, "Almacén no existe")

    s = _get_or_create_stock(db, product_id, warehouse_id)
    cur = Decimal(s.qty)

    if kind == "entrada":
        s.qty = cur + qty
        recorded_qty = qty
    elif kind == "salida":
        if qty > cur:
            raise HTTPException(400,
                f"Stock insuficiente. Disponible {cur}, solicitado {qty}")
        s.qty = cur - qty
        recorded_qty = qty
    elif kind == "ajuste":
        s.qty = qty
        recorded_qty = qty
    elif kind in ("transferencia_in", "transferencia_out"):
        # internos, ya validados por transfer()
        if kind == "transferencia_in":
            s.qty = cur + qty
        else:
            if qty > cur:
                raise HTTPException(400,
                    f"Transferencia fallida. Disponible {cur}, solicitado {qty}")
            s.qty = cur - qty
        recorded_qty = qty
    else:
        raise HTTPException(400, f"kind inválido: {kind}")

    mov = StockMovement(
        product_id=product_id, warehouse_id=warehouse_id,
        kind=kind, qty=recorded_qty,
        reason=reason, reference=reference, user_email=user_email,
    )
    db.add(mov); db.commit(); db.refresh(mov)

    # alerta reorden si cae bajo el mínimo
    try:
        if p.stock_min and Decimal(s.qty) <= Decimal(p.stock_min):
            admin_send(
                "stock_low",
                f"Stock bajo · {p.sku}",
                f"HECORP · Inventario\nProducto {p.sku} · {p.name}\n"
                f"Almacén: {w.name}\nDisponible: {s.qty} {p.unit}\n"
                f"Mínimo: {p.stock_min} {p.unit}",
            )
    except Exception:
        pass
    return mov


def transfer(db: Session, *, product_id: int, from_wh: int, to_wh: int,
             qty: Decimal, reason: Optional[str] = None,
             user_email: Optional[str] = None) -> Dict[str, StockMovement]:
    if from_wh == to_wh:
        raise HTTPException(400, "Almacenes iguales")
    out_mov = apply_movement(db,
        product_id=product_id, warehouse_id=from_wh,
        kind="transferencia_out", qty=qty,
        reason=reason or "transferencia",
        reference=f"TR→{to_wh}", user_email=user_email)
    in_mov = apply_movement(db,
        product_id=product_id, warehouse_id=to_wh,
        kind="transferencia_in", qty=qty,
        reason=reason or "transferencia",
        reference=f"TR←{from_wh}", user_email=user_email)
    return {"out": out_mov, "in": in_mov}


def list_movements(db: Session, product_id: Optional[int] = None,
                   warehouse_id: Optional[int] = None,
                   limit: int = 200) -> List[StockMovement]:
    q = db.query(StockMovement)
    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    if warehouse_id:
        q = q.filter(StockMovement.warehouse_id == warehouse_id)
    return q.order_by(StockMovement.ts.desc()).limit(limit).all()


def list_stock(db: Session, warehouse_id: Optional[int] = None) -> List[Stock]:
    q = db.query(Stock)
    if warehouse_id:
        q = q.filter(Stock.warehouse_id == warehouse_id)
    return q.order_by(Stock.id).all()


# --------------------------------------------------------------------------- #
# Delivery items (productos por entrega) + descuento al cerrar
# --------------------------------------------------------------------------- #
def attach_delivery_item(db: Session, delivery_id: int,
                         product_id: int, qty: Decimal,
                         price: Optional[Decimal] = None,
                         note: Optional[str] = None) -> DeliveryItem:
    p = db.query(Product).filter_by(id=product_id).first()
    if not p:
        raise HTTPException(400, "Producto no existe")
    item = DeliveryItem(
        delivery_id=delivery_id, product_id=product_id,
        qty=qty, price=price or p.price, note=note,
    )
    db.add(item); db.commit(); db.refresh(item)
    return item


def list_delivery_items(db: Session, delivery_id: int) -> List[DeliveryItem]:
    return db.query(DeliveryItem).filter_by(delivery_id=delivery_id).all()


def consume_delivery_stock(db: Session, delivery, warehouse_id: Optional[int] = None,
                           user_email: Optional[str] = None) -> int:
    """
    Resta stock de los productos vinculados a la entrega.
    Idempotente: usa reference='ENT-XXXX' y no descuenta dos veces.
    """
    items = list_delivery_items(db, delivery.id)
    if not items:
        return 0

    if not warehouse_id:
        warehouse_id = get_default_warehouse(db).id

    # ya hay un movimiento de salida con esta referencia? -> idempotente
    ref = delivery.code
    already = (db.query(StockMovement)
               .filter(StockMovement.reference == ref,
                       StockMovement.kind == "salida")
               .first())
    if already:
        return 0

    consumed = 0
    for it in items:
        try:
            apply_movement(db,
                product_id=it.product_id, warehouse_id=warehouse_id,
                kind="salida", qty=Decimal(it.qty),
                reason="entrega", reference=ref, user_email=user_email)
            consumed += 1
        except HTTPException as e:
            # registra incidencia de stock pero no detiene la entrega
            try:
                admin_send(
                    "stock_short",
                    f"Stock corto en {ref}",
                    f"No se pudo descontar producto id={it.product_id} qty={it.qty}: {e.detail}",
                )
            except Exception:
                pass
    return consumed


# --------------------------------------------------------------------------- #
# Alertas de reorden (consumido por cron)
# --------------------------------------------------------------------------- #
def check_low_stock(db: Session) -> Dict[str, Any]:
    """Detecta productos con total_qty <= stock_min y alerta."""
    products = db.query(Product).filter(Product.active == 1,
                                         Product.stock_min > 0).all()
    low = []
    for p in products:
        total = (db.query(func.coalesce(func.sum(Stock.qty), 0))
                 .filter(Stock.product_id == p.id).scalar() or ZERO)
        if Decimal(total) <= Decimal(p.stock_min):
            low.append({
                "id": p.id, "sku": p.sku, "name": p.name,
                "total": str(total), "min": str(p.stock_min), "unit": p.unit,
            })
    if low:
        try:
            lines = "\n".join([f"• {x['sku']} · {x['name']}: {x['total']} {x['unit']} (mín {x['min']})"
                                for x in low[:10]])
            admin_send("stock_reorder",
                       f"Reorden · {len(low)} productos bajos",
                       f"HECORP · Inventario\nProductos por debajo del mínimo:\n{lines}")
        except Exception:
            pass
    return {"low_count": len(low), "items": low}


def kpi_inventory(db: Session) -> Dict[str, Any]:
    total_products = db.query(func.count(Product.id)).filter(Product.active == 1).scalar() or 0
    total_warehouses = db.query(func.count(Warehouse.id)).filter(Warehouse.active == 1).scalar() or 0
    total_units = db.query(func.coalesce(func.sum(Stock.qty), 0)).scalar() or 0
    low = check_low_stock(db)
    return {
        "total_products": int(total_products),
        "total_warehouses": int(total_warehouses),
        "total_units": float(total_units),
        "low_count": low["low_count"],
        "low_items": low["items"][:5],
    }
