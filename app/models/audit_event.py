import uuid, datetime as dt
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, TIMESTAMP
from app.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts: Mapped[dt.datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    process_type: Mapped[str] = mapped_column(String(32))   # "agenda"|"bot"|"sms"|"tracking"|"mail"|...
    process_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    action: Mapped[str] = mapped_column(String(32))         # "create"|"update"|"send"|"retry"|"delivered"|...
    status: Mapped[str] = mapped_column(String(16))         # "success"|"fail"
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
