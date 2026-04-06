# app/crud/evento_crud.py
from sqlalchemy.orm import Session
from app.models.models import Evento
from datetime import date

# Crear evento
def crear_evento(db: Session, titulo: str, descripcion: str, fecha: date):
    evento = Evento(titulo=titulo, descripcion=descripcion, fecha=fecha)
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento

# Obtener un evento por id
def obtener_evento(db: Session, evento_id: int):
    return db.query(Evento).filter(Evento.id == evento_id).first()

# Obtener todos los eventos
def listar_eventos(db: Session):
    return db.query(Evento).order_by(Evento.fecha).all()

# Actualizar evento
def actualizar_evento(db: Session, evento_id: int, titulo: str = None, descripcion: str = None, fecha: date = None):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        return None
    if titulo:
        evento.titulo = titulo
    if descripcion:
        evento.descripcion = descripcion
    if fecha:
        evento.fecha = fecha
    db.commit()
    db.refresh(evento)
    return evento

# Eliminar evento
def eliminar_evento(db: Session, evento_id: int):
    evento = db.query(Evento).filter(Evento.id == evento_id).first()
    if not evento:
        return None
    db.delete(evento)
    db.commit()
    return evento
