from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.core.auth import verify_admin
from app.database.crud import get_all_brand_profiles

router = APIRouter(prefix="/api/v1/report", tags=["Report"])

@router.get("/branding")
def get_branding_report(
    dealer_id: Optional[str] = Query(None, description="Mã đại lý"),
    brand_name: Optional[str] = Query(None, description="Tên thương hiệu"),
    city: Optional[str] = Query(None, description="Tên thành phố"),
    ward: Optional[str] = Query(None, description="Phường/Xã"),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    limit: int = Query(20, ge=1, le=100, description="Số lượng item/trang"),
    is_admin: bool = Depends(verify_admin)
):
    """
    📊 API lấy danh sách hồ sơ thương hiệu (Branding Report)
    - Có thể lọc theo dealer_id, brand_name, city, ward
    - Hỗ trợ phân trang
    - Chỉ admin mới truy cập được (xác thực bằng middleware)
    """
    try:
        # --- Lấy toàn bộ dữ liệu từ DB ---
        all_profiles = get_all_brand_profiles()

        # --- Lọc dữ liệu ---
        filtered = []
        for p in all_profiles:
            if dealer_id and dealer_id.lower() not in p.get("dealer_id", "").lower():
                continue
            if brand_name and brand_name.lower() not in p.get("brand_name_full", "").lower():
                continue
            if city and city.lower() not in p.get("location", {}).get("city", "").lower():
                continue
            if ward and ward.lower() not in p.get("location", {}).get("ward", "").lower():
                continue
            filtered.append(p)

        # --- Phân trang ---
        total_count = len(filtered)
        start = (page - 1) * limit
        end = start + limit
        paginated = filtered[start:end]
        total_pages = max(1, (total_count + limit - 1) // limit)

        # --- Trả về kết quả ---
        return {
            "metadata": {
                "currentPage": page,
                "pageSize": limit,
                "totalPages": total_pages,
                "totalCount": total_count,
            },
            "data": paginated
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy báo cáo: {str(e)}")
