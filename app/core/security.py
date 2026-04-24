from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Expiración del refresh (días). Configurable por env, default 7.
import os
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Crea access_token con type='access'. Mantiene firma original."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Crea refresh_token con type='refresh' y expiración larga."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    """Decodifica y valida un JWT. Devuelve payload o None si inválido.
    Si expected_type se da, valida que payload['type'] coincida."""
    if not token:
        return None
    try:
        # Soporta prefijo 'Bearer '
        if token.startswith("Bearer "):
            token = token[len("Bearer "):]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            # Tolerante con tokens legacy que no tenían 'type'
            if expected_type == "access" and "type" not in payload:
                return payload
            return None
        return payload
    except JWTError:
        return None
