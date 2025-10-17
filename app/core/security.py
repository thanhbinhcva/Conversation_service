# core/security.py
import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def create_access_token(data: dict, expires_delta=None):
    """Tạo JWT token tự động (hỗ trợ cả int hoặc timedelta)."""
    to_encode = data.copy()

    if expires_delta is None:
        # Nếu config là số phút (int)
        if isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int):
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # Nếu config là timedelta
        elif isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, timedelta):
            expire = datetime.utcnow() + settings.ACCESS_TOKEN_EXPIRE_MINUTES
        else:
            raise TypeError("ACCESS_TOKEN_EXPIRE_MINUTES phải là int hoặc timedelta")
    else:
        # Nếu truyền expires_delta thủ công
        if isinstance(expires_delta, timedelta):
            expire = datetime.utcnow() + expires_delta
        elif isinstance(expires_delta, int):
            expire = datetime.utcnow() + timedelta(minutes=expires_delta)
        else:
            raise TypeError("expires_delta phải là int hoặc timedelta")

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str):
    """Giải mã JWT token."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
