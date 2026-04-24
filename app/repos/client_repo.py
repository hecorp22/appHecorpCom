from typing import List
from app.models.client import Client
from app.repos.base_repo import BaseRepo


class ClientRepo(BaseRepo[Client]):
    model = Client

    def search(self, q: str, limit: int = 100, offset: int = 0) -> List[Client]:
        query = self.db.query(Client)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(
                (Client.name.ilike(like))
                | (Client.phone.ilike(like))
                | (Client.account_key.ilike(like))
                | (Client.city.ilike(like))
            )
        return query.order_by(Client.id.desc()).offset(offset).limit(limit).all()
