from typing import List
from app.models.provider import Provider
from app.models.provider_account import ProviderAccount
from app.repos.base_repo import BaseRepo


class ProviderRepo(BaseRepo[Provider]):
    model = Provider

    def search(self, q: str, limit: int = 100, offset: int = 0) -> List[Provider]:
        query = self.db.query(Provider)
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(
                (Provider.name.ilike(like))
                | (Provider.email.ilike(like))
                | (Provider.phone.ilike(like))
            )
        return query.order_by(Provider.id.desc()).offset(offset).limit(limit).all()


class ProviderAccountRepo(BaseRepo[ProviderAccount]):
    model = ProviderAccount

    def list_by_provider(self, provider_id: int) -> List[ProviderAccount]:
        return (
            self.db.query(ProviderAccount)
            .filter(ProviderAccount.provider_id == provider_id)
            .order_by(ProviderAccount.id.desc())
            .all()
        )

    def by_id_for_provider(self, provider_id: int, account_id: int):
        return (
            self.db.query(ProviderAccount)
            .filter(
                ProviderAccount.id == account_id,
                ProviderAccount.provider_id == provider_id,
            )
            .first()
        )
