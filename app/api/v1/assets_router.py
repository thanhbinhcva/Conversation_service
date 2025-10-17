# routers/assets_router.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Header, Depends
from botocore.client import Config
import boto3
import os
from dotenv import load_dotenv
import uuid
from pydantic import BaseModel
from typing import List, Optional
from app.database.crud import save_logo_emblem, update_logo_emblem_in_db, delete_logo_emblem_from_db
from bson import ObjectId
from app.core.auth import verify_admin
# --- Load biến môi trường ---
load_dotenv()

R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "supersecrettoken")

if not all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_ACCOUNT_ID, R2_BUCKET_NAME]):
    raise RuntimeError("⚠️ Thiếu thông tin R2 trong file .env!")

# --- Endpoint URL cho Cloudflare R2 ---
R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# --- Khởi tạo client boto3 ---
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)

# --- Khởi tạo Router ---
router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])


# -----------------------------
# ✅ API upload file lên R2
# -----------------------------
@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    auth: bool = Depends(verify_admin)
):
    """Upload file (png/svg/jpg/ico/...) lên Cloudflare R2"""

    # 2️⃣ Kiểm tra định dạng file
    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in [".png", ".jpg", ".jpeg", ".svg", ".ico"]:
        raise HTTPException(status_code=400, detail="Định dạng file không được hỗ trợ.")

    # 3️⃣ Tạo tên file duy nhất
    unique_name = f"{uuid.uuid4().hex}{ext}"

    try:
        # 4️⃣ Upload lên Cloudflare R2
        s3.upload_fileobj(
            file.file,
            R2_BUCKET_NAME,
            unique_name,
            ExtraArgs={
                "ContentType": file.content_type,
                "ACL": "public-read"
            },
        )

        # 5️⃣ Tạo URL public
        public_url = f"https://pub-{R2_ACCOUNT_ID}.r2.dev/{unique_name}"

        return {
            "status": "done",
            "url": public_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload: {str(e)}")


# -----------------------------
# ✅ API thêm nhóm biểu tượng logo
# -----------------------------

# --- Models ---
class EmblemVariant(BaseModel):
    variantName: str
    url: str

class EmblemGroup(BaseModel):
    emblemId: Optional[str]
    category: str
    variant: List[EmblemVariant]

# --- API thêm nhóm biểu tượng ---
@router.post("/logo/emblem/add")
def add_logo_emblem(data: EmblemGroup, auth: bool = Depends(verify_admin)):
    """
    ➕ API: Thêm nhóm biểu tượng logo mới
    - Endpoint: /api/v1/assets/logo/emblem/add
    - Header: Authorization: Bearer <token>
    - Body:
        {
            "category": "door",
            "variant": [
                {"variantName": "door1", "url": "https://..."},
                {"variantName": "door2", "url": "https://..."}
            ]
        }
    """
    try:
        # Lưu vào MongoDB
        inserted_id = save_logo_emblem(data.dict())
        if not inserted_id:
            raise HTTPException(status_code=500, detail="Không thể lưu emblem vào cơ sở dữ liệu")

        return {
            "status": "done",
            "data": data.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm emblem: {str(e)}")

@router.put("/logo/emblem/edit")
def update_logo_emblem(data: EmblemGroup, auth: bool = Depends(verify_admin)):
    """Cập nhật thông tin nhóm biểu tượng (emblem group)"""

    # 2️⃣ Kiểm tra có emblemId không
    if not data.emblemId:
        raise HTTPException(status_code=400, detail="Thiếu trường emblemId để cập nhật")

    try:
        updated = update_logo_emblem_in_db(
            emblem_id=data.emblemId,
            category=data.category,
            variants=[v.dict() for v in data.variant]
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy emblem cần cập nhật")

        return {
            "status": "done",
            "data": {
                "category": data.category,
                "emblemId": data.emblemId,
                "variant": [v.dict() for v in data.variant]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật emblem: {str(e)}")

# --- API xóa nhóm biểu tượng ---
@router.delete("/logo/emblem/delete")
def delete_logo_emblem(data: EmblemGroup, auth: bool = Depends(verify_admin)):
    """Xóa nhóm biểu tượng (emblem group) theo emblemId"""

    # 2️⃣ Kiểm tra emblemId
    if not data.emblemId:
        raise HTTPException(status_code=400, detail="Thiếu emblemId để xóa")

    try:
        deleted = delete_logo_emblem_from_db(data.emblemId)
        if not deleted:
            raise HTTPException(status_code=404, detail="Không tìm thấy emblem cần xóa")

        return {"status": "done"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa emblem: {str(e)}")
