from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class ProviderAccount(Base):
    __tablename__ = "provider_accounts"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True)

    bank_name = Column(String(120), nullable=False)
    account_holder = Column(String(160), nullable=False)
    clabe = Column(String(18), nullable=True)         # 18 dígitos
    account_number = Column(String(30), nullable=True)
    currency = Column(String(8), nullable=False, default="MXN")  # MXN / USD
    notes = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    provider = relationship("Provider", back_populates="accounts")
