from typing import List
from fastapi import APIRouter, Depends, Query

from app.schemas.provider_schema import ProviderCreate, ProviderOut
from app.services.provider_service import ProviderService
from app.core.deps import get_provider_service
from app.core.auth_deps import require_admin, require_user
from app.models.user_model import User

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=List[ProviderOut])
@router.get("/", response_model=List[ProviderOut])
def list_providers(
    q: str = Query("", max_length=80),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_user),
):
    return svc.list(q=q, limit=limit, offset=offset)


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider(
    provider_id: int,
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_user),
):
    return svc.get(provider_id)


@router.post("", response_model=ProviderOut)
@router.post("/", response_model=ProviderOut)
def create_provider(
    data: ProviderCreate,
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_admin),
):
    return svc.create(data)


@router.delete("/{provider_id}")
def delete_provider(
    provider_id: int,
    svc: ProviderService = Depends(get_provider_service),
    _: User = Depends(require_admin),
):
    svc.delete(provider_id)
    return {"ok": True}
