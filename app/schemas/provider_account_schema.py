from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

CLABE_RE = re.compile(r"^\d{18}$")


class ProviderAccountCreate(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=120)
    account_holder: str = Field(..., min_length=2, max_length=160)
    clabe: str | None = Field(None, description="CLABE 18 dígitos (opcional)")
    account_number: str | None = Field(None, max_length=30)
    currency: str = Field("MXN", pattern="^(MXN|USD|EUR)$")
    notes: str | None = Field(None, max_length=255)

    @field_validator("clabe")
    @classmethod
    def val_clabe(cls, v):
        if v in (None, "", " "):
            return None
        v = v.strip()
        if not CLABE_RE.match(v):
            raise ValueError("CLABE debe tener 18 dígitos")
        return v


class ProviderAccountOut(ProviderAccountCreate):
    id: int
    provider_id: int
    model_config = ConfigDict(from_attributes=True)
