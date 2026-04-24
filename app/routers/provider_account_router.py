from typing import List
from fastapi import APIRouter, Depends

from app.schemas.provider_account_schema import ProviderAccountCreate, ProviderAccountOut
from app.services.provider_service import ProviderService
from app.core.deps import get_provider_service
from app.core.auth_deps import require_admin, require_user
from app.models.user_model import User

router = APIRouter(prefix="/providers/{provider_id}/accounts", tags=["provider-accounts"])


@router.get("", response_model=List[ProviderAccountOut])
@router.get("/", response_model=List[ProviderAccountOut])
def list_accounts(
    provider_id: int,
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_user),
):
    return svc.list_accounts(provider_id)


@router.post("", response_model=ProviderAccountOut)
@router.post("/", response_model=ProviderAccountOut)
def create_account(
    provider_id: int,
    data: ProviderAccountCreate,
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_admin),
):
    return svc.create_account(provider_id, data)


@router.delete("/{account_id}")
def delete_account(
    provider_id: int,
    account_id: int,
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_admin),
):
    svc.delete_account(provider_id, account_id)
    return {"ok": True}
