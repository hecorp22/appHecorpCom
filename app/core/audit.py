from sqlalchemy.orm import Session
from app.models.audit_event import AuditEvent
from app.core.context import ctx_trace_id, ctx_process_type, ctx_process_id, ctx_tenant, ctx_user
from loguru import logger

def audit(db: Session, action: str, status: str, details: dict | None = None):
    evt = AuditEvent(
        tenant_id=ctx_tenant.get(),
        user_email=ctx_user.get(),
        process_type=ctx_process_type.get() or "unknown",
        process_id=ctx_process_id.get(),
        action=action,
        status=status,
        trace_id=ctx_trace_id.get(),
        details=details or {}
    )
    db.add(evt)
    db.commit()
    # Log técnico a la par (para correlación)
    logger.bind(
        trace_id=evt.trace_id,
        process_type=evt.process_type,
        process_id=evt.process_id,
        tenant=evt.tenant_id,
        user=evt.user_email
    ).info("audit_event", action=action, status=status, details=details)
