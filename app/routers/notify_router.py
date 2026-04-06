from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.sms_service import SmsService
from loguru import logger
from app.core.context import ctx_process_type, ctx_process_id, bind_context
# si quieres guardar auditoría:
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.core.audit import audit

router = APIRouter(prefix="/notify", tags=["notify"])

class SmsReq(BaseModel):
    to: str = Field(..., example="+52XXXXXXXXXX")
    body: str = Field(..., max_length=1000)
    process_type: str | None = "sms"
    process_id: str | None = None

@router.post("/sms")
def send_sms(req: SmsReq):
    # contexto para logs/métricas
    if req.process_type: ctx_process_type.set(req.process_type)
    if req.process_id:   ctx_process_id.set(req.process_id)
    log = bind_context(logger)

    svc = SmsService()
    try:
        sid = svc.send(req.to, req.body)
        log.info("sms_sent", to=req.to, provider_msg_id=sid)
        # audit(db, action="send", status="success", details={"channel":"sms","to":req.to,"sid":sid})
        return {"ok": True, "sid": sid}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SMS error: {e}")
