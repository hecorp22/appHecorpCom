from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr

from app.schemas.quotation_schema import QuotationCreate, QuotationOut
from app.services.quotation_service import QuotationService
from app.services.quotation_pdf import build_quotation_pdf
from app.services.email_service import send_email
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


_COMPANY_INFO = {
    "phone": "+52 272 000 0000",
    "email": "ventas@aleacionesymaquinados.mx",
    "tagline": "Aleaciones · Maquinados · Precisión",
}


@router.get("/{quote_id}/pdf")
def pdf_quotation(
    quote_id: int,
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_user),
):
    q = svc.get(quote_id)
    pdf = build_quotation_pdf(q, company_info=_COMPANY_INFO)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{q.quote_code}.pdf"'},
    )


class QuotationEmailReq(BaseModel):
    to: Optional[EmailStr] = None   # si se omite, usa q.email
    cc: Optional[List[EmailStr]] = None
    subject: Optional[str] = None
    message: Optional[str] = None


@router.post("/{quote_id}/email")
def email_quotation(
    quote_id: int,
    req: QuotationEmailReq,
    svc: QuotationService = Depends(get_quotation_service),
    _: User = Depends(require_admin),
):
    q = svc.get(quote_id)
    to = req.to or q.email
    if not to:
        raise HTTPException(status_code=400, detail="La cotización no tiene correo y no se proporcionó uno")

    pdf = build_quotation_pdf(q, company_info=_COMPANY_INFO)

    subject = req.subject or f"Cotización {q.quote_code} · Aleaciones y Maquinados"
    greeting = f"Estimado(a) {q.contact_name}" if q.contact_name else "Estimado(a)"
    extra = (req.message or "").strip()
    extra_html = f"<p>{extra.replace(chr(10), '<br/>')}</p>" if extra else ""

    html = f"""<!DOCTYPE html>
<html><body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#0F1A22;background:#FDFBF6;padding:20px">
  <div style="max-width:600px;margin:auto;background:#fff;border:1px solid #E3C492;border-radius:8px;overflow:hidden">
    <div style="background:#0A6E7A;color:#FDFBF6;padding:18px 22px">
      <h1 style="margin:0;font-size:18px;letter-spacing:.04em">ALEACIONES Y MAQUINADOS</h1>
      <p style="margin:4px 0 0;font-size:12px;color:#B8E4E8">Aleaciones · Maquinados · Precisión</p>
    </div>
    <div style="padding:22px;font-size:14px;line-height:1.55">
      <p>{greeting},</p>
      <p>Adjunto encontrará la cotización solicitada <strong>{q.quote_code}</strong>
         para <em>{q.company}</em>.</p>
      <p><strong>Asunto:</strong> {q.subject}<br/>
         <strong>Total:</strong> ${q.total} {q.currency}</p>
      {extra_html}
      <p style="margin-top:22px">Quedamos al pendiente para cualquier aclaración.</p>
      <p style="margin:20px 0 0;color:#6B7A85;font-size:12px;border-top:1px solid #E3C492;padding-top:12px">
        Aleaciones y Maquinados · Orizaba, Ver. · ventas@aleacionesymaquinados.mx
      </p>
    </div>
  </div>
</body></html>"""

    text = (
        f"{greeting},\n\nAdjunto cotización {q.quote_code} para {q.company}.\n"
        f"Asunto: {q.subject}\nTotal: ${q.total} {q.currency}\n\n"
        + (extra + "\n\n" if extra else "")
        + "Aleaciones y Maquinados\n"
    )

    ok, mid, err = send_email(
        to=to,
        cc=req.cc,
        subject=subject,
        html=html,
        text=text,
        attachments=[{
            "filename": f"{q.quote_code}.pdf",
            "content": pdf,
            "content_type": "application/pdf",
        }],
    )
    if not ok:
        raise HTTPException(status_code=502, detail=f"No se pudo enviar: {err}")
    return {"ok": True, "message_id": mid, "to": to, "quote_code": q.quote_code}
