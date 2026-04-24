from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
import re


PHONE_RE = re.compile(r"^\d{10}$")


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    contact: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(..., description="10 dígitos")
    address: str = Field(..., min_length=3, max_length=255)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = (v or "").strip()
        if not PHONE_RE.match(v):
            raise ValueError("Teléfono debe tener exactamente 10 dígitos")
        return v

    @field_validator("name", "contact", "address")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ProviderOut(ProviderCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
