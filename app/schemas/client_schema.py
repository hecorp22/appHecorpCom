from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


PHONE_RE = re.compile(r"^\d{10}$")


class ClientCreate(BaseModel):
    phone: str = Field(..., description="10 dígitos, solo números")
    account_key: str = Field(..., min_length=2, max_length=50)
    address: str = Field(..., min_length=3, max_length=255)
    name: str = Field(..., min_length=2, max_length=120)
    state: str = Field(..., min_length=2, max_length=80)
    country: str = Field(..., min_length=2, max_length=80)
    city: str = Field(..., min_length=2, max_length=80)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = (v or "").strip()
        if not PHONE_RE.match(v):
            raise ValueError("Teléfono debe tener exactamente 10 dígitos")
        return v

    @field_validator("name", "address", "state", "country", "city", "account_key")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class ClientOut(ClientCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
