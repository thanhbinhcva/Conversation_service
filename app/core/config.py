import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load các biến môi trường từ file .env
load_dotenv()

class Settings(BaseSettings):
    # === API Keys ===
    GEMINI_API_KEY: str

    # === MongoDB ===
    MONGO_URI: str

    # === Cloudflare R2 ===
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str
    R2_ACCOUNT_ID: str
    R2_BUCKET_NAME: str

    # === JWT & Ứng dụng ===
    PROJECT_NAME: str = "AI Brand Assistant"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkey")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    # SESSION_EXPIRATION_HOURS: int = 4

    class Config:
        env_file = ".env"  # đọc biến từ file .env

# Khởi tạo settings để import toàn hệ thống
settings = Settings()
