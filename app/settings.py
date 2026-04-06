from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator

class Settings(BaseSettings):
    algorithm: str
    access_token_expire_minutes: int
    vps_url: str
    allowed_origins: List[str]
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_sms_from: str
    telegram_bot_token: str
    telegram_bot_chat_id: str
    telegram_group_chat_id: str
    recovery_code: str
    page_id: str
    page_token: str

    class Config:
        env_file = ".env"
        extra = "allow"

    # Este validador transforma el CSV a lista antes de la validación
    @field_validator("allowed_origins", mode="before")
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        return v

settings = Settings()
