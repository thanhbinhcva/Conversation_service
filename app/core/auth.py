from fastapi import HTTPException, Header, Depends
from typing import Optional
import jwt
from app.core.config import settings
from app.core.security import decode_token

def get_current_user(authorization: Optional[str] = Header(None)):
    """Lấy thông tin user từ JWT"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu Authorization header")

    token = authorization.replace("Bearer", "").strip()

    try:
        payload = decode_token(token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ.")


def verify_admin(payload: dict = Depends(get_current_user)):
    """Xác thực quyền admin"""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền admin.")
    return payload
