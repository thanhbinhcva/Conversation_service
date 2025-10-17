# app/api/v1/auth_route.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import timedelta
from app.database.crud import create_user, find_user_by_username, verify_password
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# ------------------------
# 🧩 Schema định nghĩa request/response
# ------------------------

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    status: str
    token: str | None = None
    user: dict | None = None


# ------------------------
# 🧱 API ROUTES
# ------------------------

@router.post("/register", response_model=AuthResponse)
def register_user(req: RegisterRequest):
    """Đăng ký người dùng mới"""
    user = create_user(req.username, req.password, req.role)
    if not user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại.")

    token_data = {
        "user_id": user["_id"],
        "username": user["username"],
        "role": user["role"],
    }

    token = create_access_token(
        token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "status": "success",
        "token": token,
        "user": {"username": user["username"], "role": user["role"]},
    }


@router.post("/login", response_model=AuthResponse)
def login_user(req: LoginRequest):
    """Đăng nhập và nhận JWT"""
    user = find_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu sai.")

    token_data = {
        "user_id": user["_id"],
        "username": user["username"],
        "role": user["role"],
    }

    token = create_access_token(
        token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "status": "success",
        "token": token,
        "user": {"username": user["username"], "role": user["role"]},
    }
