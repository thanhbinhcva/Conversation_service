from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv

from database import create_user, find_user_by_username, verify_password

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 6

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Sinh token động"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register")
def register_user(req: RegisterRequest):
    user = create_user(req.username, req.password, req.role)
    if not user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại.")
    return {
        "status": "success",
        "user": {"username": user["username"], "role": user["role"]}
    }

@router.post("/login")
def login_user(req: LoginRequest):
    user = find_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu sai.")

    token = create_access_token({
        "user_id": user["_id"],
        "username": user["username"],
        "role": user["role"]
    })

    return {"status": "success", "token": token}
