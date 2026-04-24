"""
Factories de repositorios y servicios. Úsalas con Depends(...) en los routers.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

# repos
from app.repos.client_repo import ClientRepo
from app.repos.provider_repo import ProviderRepo, ProviderAccountRepo
from app.repos.order_repo import OrderRepo
from app.repos.shipment_repo import ShipmentRepo, ShipmentPhotoRepo
from app.repos.quotation_repo import QuotationRepo

# services
from app.services.client_service import ClientService
from app.services.provider_service import ProviderService
from app.services.order_service import OrderService
from app.services.shipment_service import ShipmentService
from app.services.quotation_service import QuotationService


# ---- repos ----
def get_client_repo(db: Session = Depends(get_db)) -> ClientRepo:
    return ClientRepo(db)


def get_provider_repo(db: Session = Depends(get_db)) -> ProviderRepo:
    return ProviderRepo(db)


def get_provider_account_repo(db: Session = Depends(get_db)) -> ProviderAccountRepo:
    return ProviderAccountRepo(db)


def get_order_repo(db: Session = Depends(get_db)) -> OrderRepo:
    return OrderRepo(db)


def get_shipment_repo(db: Session = Depends(get_db)) -> ShipmentRepo:
    return ShipmentRepo(db)


def get_shipment_photo_repo(db: Session = Depends(get_db)) -> ShipmentPhotoRepo:
    return ShipmentPhotoRepo(db)


def get_quotation_repo(db: Session = Depends(get_db)) -> QuotationRepo:
    return QuotationRepo(db)


# ---- services ----
def get_client_service(
    repo: ClientRepo = Depends(get_client_repo),
) -> ClientService:
    return ClientService(repo)


def get_provider_service(
    repo: ProviderRepo = Depends(get_provider_repo),
    acc_repo: ProviderAccountRepo = Depends(get_provider_account_repo),
) -> ProviderService:
    return ProviderService(repo, acc_repo)


def get_order_service(
    repo: OrderRepo = Depends(get_order_repo),
    client_repo: ClientRepo = Depends(get_client_repo),
) -> OrderService:
    return OrderService(repo, client_repo)


def get_shipment_service(
    repo: ShipmentRepo = Depends(get_shipment_repo),
    photo_repo: ShipmentPhotoRepo = Depends(get_shipment_photo_repo),
    client_repo: ClientRepo = Depends(get_client_repo),
    order_repo: OrderRepo = Depends(get_order_repo),
) -> ShipmentService:
    return ShipmentService(repo, photo_repo, client_repo, order_repo)


def get_quotation_service(
    repo: QuotationRepo = Depends(get_quotation_repo),
) -> QuotationService:
    return QuotationService(repo)
