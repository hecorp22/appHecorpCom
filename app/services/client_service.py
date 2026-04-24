from typing import List
from fastapi import HTTPException
from app.models.client import Client
from app.repos.client_repo import ClientRepo
from app.schemas.client_schema import ClientCreate


class ClientService:
    def __init__(self, repo: ClientRepo):
        self.repo = repo

    def list(self, q: str = "", limit: int = 200, offset: int = 0) -> List[Client]:
        return self.repo.search(q, limit=limit, offset=offset)

    def get(self, client_id: int) -> Client:
        obj = self.repo.by_id(client_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return obj

    def create(self, data: ClientCreate) -> Client:
        c = Client(
            phone=data.phone,
            account_key=data.account_key,
            address=data.address,
            name=data.name,
            state=data.state,
            country=data.country,
            city=data.city,
        )
        return self.repo.add(c)

    def delete(self, client_id: int) -> None:
        obj = self.get(client_id)
        self.repo.delete(obj)
