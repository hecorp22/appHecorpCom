from typing import List
from fastapi import HTTPException
from app.models.provider import Provider
from app.models.provider_account import ProviderAccount
from app.repos.provider_repo import ProviderRepo, ProviderAccountRepo
from app.schemas.provider_schema import ProviderCreate
from app.schemas.provider_account_schema import ProviderAccountCreate


class ProviderService:
    def __init__(self, repo: ProviderRepo, account_repo: ProviderAccountRepo):
        self.repo = repo
        self.account_repo = account_repo

    # ---- providers ----
    def list(self, q: str = "", limit: int = 200, offset: int = 0) -> List[Provider]:
        return self.repo.search(q, limit=limit, offset=offset)

    def get(self, provider_id: int) -> Provider:
        obj = self.repo.by_id(provider_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return obj

    def create(self, data: ProviderCreate) -> Provider:
        p = Provider(
            name=data.name,
            contact=data.contact,
            email=data.email,
            phone=data.phone,
            address=data.address,
        )
        return self.repo.add(p)

    def delete(self, provider_id: int) -> None:
        self.repo.delete(self.get(provider_id))

    # ---- accounts ----
    def list_accounts(self, provider_id: int) -> List[ProviderAccount]:
        self.get(provider_id)  # 404 si no existe
        return self.account_repo.list_by_provider(provider_id)

    def create_account(self, provider_id: int, data: ProviderAccountCreate) -> ProviderAccount:
        self.get(provider_id)
        acc = ProviderAccount(
            provider_id=provider_id,
            bank_name=data.bank_name,
            account_holder=data.account_holder,
            clabe=data.clabe,
            account_number=data.account_number,
            currency=data.currency,
            notes=data.notes,
        )
        return self.account_repo.add(acc)

    def delete_account(self, provider_id: int, account_id: int) -> None:
        acc = self.account_repo.by_id_for_provider(provider_id, account_id)
        if not acc:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        self.account_repo.delete(acc)
