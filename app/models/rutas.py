from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base  # tu Base declarative

class Ruta(Base):
    __tablename__ = "rutas"
    __table_args__ = {"schema": "hecorp_schema"}  # tu schema

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    user_id = Column(String(100), index=True, nullable=False)   # ajusta a tu tipo real (int si usas ids numéricos)
    owner_id = Column(String(100), nullable=False)      # 👈 nuevo
    origen_lat = Column(Float, nullable=False)
    origen_lng = Column(Float, nullable=False)
    destino_lat = Column(Float, nullable=False)
    destino_lng = Column(Float, nullable=False)
    distancia_km = Column(Float, nullable=False)    # e.g. 12.34
    duracion_min = Column(Integer, nullable=False)  # e.g. 25
    geojson = Column(JSONB, nullable=False)         # LineString completo
    notas = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
