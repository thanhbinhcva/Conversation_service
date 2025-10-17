from fastapi import APIRouter, HTTPException, Query
from app.database.crud import get_brand_profile_by_session

router = APIRouter(prefix="/api/v1/logo", tags=["Branding"])


@router.get("/getBranding")
def get_branding_public(
    session_id: str = Query(..., description="Session ID của phiên trò chuyện với AI")
):
    """
    🔍 Lấy thông tin hồ sơ thương hiệu (brand_profile) theo session_id.
    - Không yêu cầu quyền admin.
    - Dành cho người dùng hoặc AI khác cần truy xuất dữ liệu hồ sơ thương hiệu.
    - Output JSON theo cấu trúc chuẩn.
    """
    try:
        # --- Lấy dữ liệu từ MongoDB ---
        doc = get_brand_profile_by_session(session_id)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy hồ sơ thương hiệu với session_id này."
            )

        # --- Chuẩn hóa dữ liệu ---
        def safe_list(value):
            """Đảm bảo trả về list, ngay cả khi là None hoặc string"""
            if isinstance(value, list):
                return value
            if isinstance(value, str) and value.strip():
                return [value.strip()]
            return []

        def safe_location(loc):
            """Đảm bảo location luôn có đủ 4 field"""
            if not isinstance(loc, dict):
                return {"number": "", "street": "", "ward": "", "city": ""}
            return {
                "number": loc.get("number", ""),
                "street": loc.get("street", ""),
                "ward": loc.get("ward", ""),
                "city": loc.get("city", "")
            }

        def safe_product_portfolio(portfolio):
            """Đảm bảo product_portfolio là danh sách object có product & rate"""
            result = []
            if isinstance(portfolio, list):
                for item in portfolio:
                    if isinstance(item, dict):
                        result.append({
                            "product": item.get("product", ""),
                            "rate": item.get("rate", "")
                        })
                    elif isinstance(item, str):
                        result.append({"product": item, "rate": ""})
            return result

        # --- Chuẩn hóa dữ liệu trả về ---
        response = {
            "session_id": doc.get("session_id", ""),
            "dealer_id": doc.get("dealer_id", ""),
            "brand_name_full": doc.get("brand_name_full", ""),
            "location": safe_location(doc.get("location", {})),
            "main_services": safe_list(doc.get("main_services")),
            "product_portfolio": safe_product_portfolio(doc.get("product_portfolio")),
            "target_customers": safe_list(doc.get("target_customers")),
            "competitive_advantage": safe_list(doc.get("competitive_advantage")),
            "core_values": safe_list(doc.get("core_values")),
            "slogan": doc.get("slogan", ""),
            "future_vision": safe_list(doc.get("future_vision")),
            "logo_style": safe_list(doc.get("logo_style")),
            "main_color": safe_list(doc.get("main_color")),
            "revenue": safe_list(doc.get("revenue"))
        }

        return {"status": "success", "data": response}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi truy xuất dữ liệu: {str(e)}"
        )
