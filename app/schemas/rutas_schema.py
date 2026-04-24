from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional

class RutaCreate(BaseModel):
    nombre: str = Field(..., max_length=200)
    origen_lat: float
    origen_lng: float
    destino_lat: float
    destino_lng: float
    distancia_km: float
    duracion_min: int
    geojson: Any
    notas: Optional[str] = None

class RutaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=200)
    origen_lat: Optional[float] = None
    origen_lng: Optional[float] = None
    destino_lat: Optional[float] = None
    destino_lng: Optional[float] = None
    distancia_km: Optional[float] = None
    duracion_min: Optional[int] = None
    geojson: Optional[Any] = None
    notas: Optional[str] = None

class RutaOut(BaseModel):
    id: int
    nombre: str
    user_id: str
    origen_lat: float
    origen_lng: float
    destino_lat: float
    destino_lng: float
    distancia_km: float
    duracion_min: int
    geojson: Any
    notas: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
