"""
Base Repository — acceso a DB común para todos los módulos.
Uso: heredar y fijar `model`.
"""
from typing import Generic, Type, TypeVar, Optional, List
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepo(Generic[T]):
    model: Type[T]

    def __init__(self, db: Session):
        self.db = db

    # ---- lectura ----
    def by_id(self, pk: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == pk).first()

    def exists(self, pk: int) -> bool:
        return self.db.query(self.model.id).filter(self.model.id == pk).first() is not None

    def list(self, limit: int = 500, offset: int = 0) -> List[T]:
        return (
            self.db.query(self.model)
            .order_by(self.model.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    # ---- escritura ----
    def add(self, obj: T) -> T:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        self.db.delete(obj)
        self.db.commit()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, obj: T) -> None:
        self.db.refresh(obj)
