# app/repos/route_repo.py
from sqlalchemy.orm import Session
from app.models.rutas import Ruta
from typing import List, Optional

class RouteRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, ruta_id: int) -> Optional[Ruta]:
        return self.db.query(Ruta).filter(Ruta.id == ruta_id).first()

    def list_for_user(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Ruta]:
        # devuelve rutas own + compartidas
        q = self.db.query(Ruta).filter(Ruta.owner_id == str(user_id))
        # union con compartidas:
        shared = self.db.execute(
            "SELECT r.* FROM hecorp_schema.rutas r JOIN hecorp_schema.rutas_usuarios ru ON r.id = ru.ruta_id WHERE ru.user_id = :uid",
            {"uid": str(user_id)}
        ).fetchall()
        own = q.order_by(Ruta.created_at.desc()).offset(offset).limit(limit).all()
        # combinar: own + shared (mapped rows require conversion)
        # simplificamos devolviendo own + shared raw rows => better: implement shared via ORM
        return own + [self._row_to_model(row) for row in shared]

    def create(self, ruta: Ruta) -> Ruta:
        self.db.add(ruta)
        self.db.commit()
        self.db.refresh(ruta)
        return ruta

    def delete(self, ruta: Ruta):
        self.db.delete(ruta)
        self.db.commit()

    def _row_to_model(self, row):
        # si usas result rows convert a objeto Ruta si lo necesitas
        return row
