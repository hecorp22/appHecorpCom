# app/models/evento.py
from sqlalchemy import Column, Integer, String, Date, DateTime
from datetime import datetime
from app.database import Base  # IMPORTANTE: usar el mismo Base
                                          
class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = {"schema": "hecorp_schema"}  # tu schema

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(String)
    fecha = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
