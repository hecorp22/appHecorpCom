from typing import List
from fastapi import APIRouter, Depends, Query, Form
from fastapi.responses import Response

from app.schemas.quotation_schema import QuotationCreate, QuotationOut
from app.services.quotation_service import QuotationService
from app.services.quotation_pdf import build_quotation_pdf
from app.core.deps import get_quotation_service
from app.core.auth_deps import require_admin, require_user
from app.models.user_model import User

router = APIRouter(prefix="/quotations", tags=["quotations"])


@router.get("", response_model=List[QuotationOut])
@router.get("/", response_model=List[QuotationOut])
def list_quotations(
    q: str = Query("", max_length=80),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_user),
):
    return svc.list(q=q, limit=limit, offset=offset)


@router.get("/{quote_id}", response_model=QuotationOut)
def get_quotation(
    quote_id: int,
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_user),
):
    return svc.get(quote_id)


@router.post("", response_model=QuotationOut)
@router.post("/", response_model=QuotationOut)
def create_quotation(
    data: QuotationCreate,
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_admin),
):
    return svc.create(data)


@router.patch("/{quote_id}/status", response_model=QuotationOut)
def update_status(
    quote_id: int,
    status: str = Form(...),
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_admin),
):
    return svc.update_status(quote_id, status)


@router.delete("/{quote_id}")
def delete_quotation(
    quote_id: int,
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_admin),
):
    svc.delete(quote_id)
    return {"ok": True}


@router.get("/{quote_id}/pdf")
def pdf_quotation(
    quote_id: int,
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_user),
):
    q = svc.get(quote_id)
    pdf = build_quotation_pdf(q, company_info={
        "phone": "+52 272 000 0000",
        "email": "ventas@aleacionesymaquinados.mx",
        "tagline": "Aleaciones · Maquinados · Precisión",
    })
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{q.quote_code}.pdf"'},
    )
