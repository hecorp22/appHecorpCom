# app/services/route_service.py
from app.repos.route_repo import RouteRepo
from app.policies.roles import can_access_route, can_edit_route
from sqlalchemy.orm import Session

class RouteService:
    def __init__(self, db: Session):
        self.repo = RouteRepo(db)
        self.db = db

    def get_route_for_user(self, ruta_id: int, user):
        ruta = self.repo.get_by_id(ruta_id)
        if not ruta:
            return None
        # obtener permiso compartido si existe
        perm_row = self.db.execute(
            "SELECT permiso FROM hecorp_schema.rutas_usuarios WHERE ruta_id = :rid AND user_id = :uid",
            {"rid": ruta.id, "uid": str(getattr(user, "id", ""))}
        ).fetchone()
        permiso = perm_row[0] if perm_row else None
        if not can_access_route(user, ruta.owner_id, permiso):
            raise PermissionError("No autorizado")
        return ruta

    def create_route(self, payload, user):
        from app.models.rutas import Ruta
        ruta = Ruta(
            nombre=payload.nombre,
            owner_id=str(getattr(user, "id", "")),
            origen_lat=payload.origen_lat, origen_lng=payload.origen_lng,
            destino_lat=payload.destino_lat, destino_lng=payload.destino_lng,
            distancia_km=payload.distancia_km, duracion_min=payload.duracion_min,
            geojson=payload.geojson, notas=payload.notas
        )
        return self.repo.create(ruta)

    def share_route(self, ruta_id: int, user_id: str, permiso: str = "viewer"):
        # solo owner o superuser puede compartir (check outside)
        self.db.execute(
            "INSERT INTO hecorp_schema.rutas_usuarios (ruta_id, user_id, permiso) VALUES (:rid,:uid,:perm)",
            {"rid": ruta_id, "uid": str(user_id), "perm": permiso}
        )
        self.db.commit()
