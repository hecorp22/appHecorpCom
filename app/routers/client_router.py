from typing import List
from fastapi import APIRouter, Depends, Query

from app.schemas.client_schema import ClientCreate, ClientOut
from app.services.client_service import ClientService
from app.core.deps import get_client_service
from app.core.auth_deps import require_admin, require_user
from app.models.user_model import User

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=List[ClientOut])
@router.get("/", response_model=List[ClientOut])
def list_clients(
    q: str = Query("", max_length=80),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: ClientService = Depends(get_client_service),
    _: User = Depends(require_user),
):
    return svc.list(q=q, limit=limit, offset=offset)


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    svc: ClientService = Depends(get_client_service),
    _: User = Depends(require_user),
):
    return svc.get(client_id)


@router.post("", response_model=ClientOut)
@router.post("/", response_model=ClientOut)
def create_client(
    data: ClientCreate,
    svc: ClientService = Depends(get_client_service),
    _: User = Depends(require_admin),
):
    return svc.create(data)


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    svc: ClientService = Depends(get_client_service),
    _: User = Depends(require_admin),
):
    svc.delete(client_id)
    return {"ok": True}
