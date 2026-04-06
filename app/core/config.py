from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    VPS_URL: str = os.getenv("VPS_URL")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    TELEGRAM_BOT_TOKEN: str =os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_BOT_CHAT_ID: str =os.getenv("TELEGRAM_BOT_CHAT_ID")
    TELEGRAM_GROUP_CHAT_ID: str =os.getenv("TELEGRAM_GROUP_CHAT_ID")


settings = Settings()
