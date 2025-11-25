# app/core/security.py
from datetime import datetime, timedelta, timezone
import jwt  # PyJWT
from passlib.context import CryptContext
from app.config import settings

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    exp_min = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {
        "sub": subject,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_min),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, expires_days: int | None = None) -> str:
    exp_days = expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=exp_days),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
