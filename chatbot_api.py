from fastapi import FastAPI, HTTPException, Query, Header, Depends
from pydantic import BaseModel
import uvicorn
import json
import uuid
import re
from datetime import datetime, timedelta
from main import main_prompt
from typing import Optional
import math
import os

from main import (
    main_chain, memory, extract_info,
    save_brand_profile, recommend_logo,
    generate_logo_with_ai, google_api_key
)
from database import save_to_mongo, collection, get_brand_profile_by_session, get_all_brand_profiles, get_latest_prompt, save_prompt_to_db, reset_prompt_to_default
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

app = FastAPI(title="AI Brand Assistant API v1")

# --- ENV ---
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "supersecrettoken")

# --- SESSION MANAGEMENT ---
sessions = {}  # {session_id: {"user_id": str, "expires_at": datetime, "memory": memory_object}}
SESSION_EXPIRATION_HOURS = 4


def get_or_create_session(user_id: str):
    """Tạo hoặc lấy session đang hoạt động cho user"""
    now = datetime.utcnow()

    # Kiểm tra session còn hạn
    for sid, sess in sessions.items():
        if sess["user_id"] == user_id and sess["expires_at"] > now:
            return sid, sess

    # Nếu không có session → tạo mới
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "user_id": user_id,
        "expires_at": now + timedelta(hours=SESSION_EXPIRATION_HOURS),
        "memory": memory
    }
    print(f"🆕 New session created for user {user_id}: {session_id}")
    return session_id, sessions[session_id]


# --- MODELS ---
class ChatRequest(BaseModel):
    userID: str
    text_input: str


class ChatResponse(BaseModel):
    message: str
    finished: bool
    receiverID: str
    sessionID: str

class PromptUpdateRequest(BaseModel):
    new_prompt: str

# --- HÀM PHÂN TÍCH NGỮ CẢNH XÁC NHẬN ---
def should_finalize(conversation_history: str, last_user_input: str) -> bool:
    """Dùng LLM phân tích xem người dùng có thực sự xác nhận finalize không"""
    check_prompt = ChatPromptTemplate.from_template("""
    Bạn là hệ thống phân tích hội thoại giữa người dùng và trợ lý AI xây dựng thương hiệu.
    Dựa vào toàn bộ đoạn hội thoại trước đó và tin nhắn mới nhất của người dùng,
    hãy quyết định xem người dùng có đang XÁC NHẬN rằng bản tóm tắt hồ sơ thương hiệu là "đúng và đủ"
    (tức là muốn hoàn tất và lưu kết quả), hay chỉ đồng ý ở ngữ cảnh khác.

    Trả về JSON hợp lệ:
    {{
        "finalize": true hoặc false
    }}

    ----
    Lịch sử hội thoại:
    {conversation}

    Tin nhắn mới nhất của người dùng:
    {user_input}
    """)

    chain = LLMChain(llm=main_chain.llm, prompt=check_prompt, verbose=False)
    response = chain.invoke({"conversation": conversation_history, "user_input": last_user_input})
    raw_text = response.get("text", "").strip()

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return False
    try:
        result = json.loads(match.group())
        return result.get("finalize", False)
    except Exception:
        return False


# --- MAIN CHAT ENDPOINT ---
@app.post("/api/v1/chat", response_model=ChatResponse)
def chat_with_bot(req: ChatRequest):
    """
    Endpoint chính: /api/v1/chat
    - Nhận {userID, text_input}
    - Tự tạo / tái sử dụng sessionID (hết hạn sau 4h)
    - Tự động finalize nếu người dùng xác nhận 'đúng và đủ'
    """
    try:
        # 1️⃣ Lấy hoặc tạo session
        session_id, sess_data = get_or_create_session(req.userID)
        sess_memory = sess_data["memory"]

        # 2️⃣ Chatbot phản hồi
        response = main_chain.invoke({"user_input": req.text_input})
        bot_reply = response["text"]

        # 3️⃣ Lấy lịch sử hội thoại
        history_data = sess_memory.load_memory_variables({}).get("history", "")

        # 4️⃣ Xác định xem cần finalize hay chưa
        finalized = should_finalize(history_data, req.text_input)
        if finalized:
            finalized_data = auto_finalize(sess_memory)
            bot_reply = "✅ Hồ sơ đã được tổng hợp và lưu thành công. 🚀"

        return ChatResponse(
            message=bot_reply,
            finished=finalized,
            receiverID="chatbot_brand_assistant",
            sessionID=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- FINALIZE LOGIC ---
def auto_finalize(sess_memory):
    """Tổng hợp thông tin & sinh logo"""
    try:
        final_summary = sess_memory.load_memory_variables({})["history"]
        if not final_summary:
            raise ValueError("Không có dữ liệu hội thoại để tổng hợp.")

        brand_profile = extract_info(final_summary)
        save_brand_profile(brand_profile)

        # ✅ Lưu vào MongoDB
        inserted_id = save_to_mongo(brand_profile)
        if inserted_id:
            brand_profile["_id"] = str(inserted_id)
        print(f"✅ Brand profile đã lưu MongoDB với ID: {inserted_id}")

        # --- Sinh logo ---
        logo_info = None
        logo_shape_text = " ".join(brand_profile.get("logo_shape", [])).lower()

        if any(keyword in logo_shape_text for keyword in [
            "cách điệu", "tên thương hiệu", "wordmark", "logo chữ", "logotype"
        ]):
            print("🤖 Sinh logo AI vì người dùng muốn logo cách điệu tên thương hiệu...")
            path = generate_logo_with_ai(
                brand_profile, google_api_key=google_api_key, output_path="generated_logo.png"
            )
            logo_info = {"type": "ai_generated", "file_path": path}
        else:
            suggestion = recommend_logo(final_summary)
            logo_info = {
                "type": "predefined",
                "category": suggestion["recommended_category"],
                "reason": suggestion["reason"],
                "folder_path": suggestion["folder_path"]
            }

        return {"brand_profile": brand_profile, "logo_info": logo_info}

    except Exception as e:
        print("❌ Lỗi khi finalize:", str(e))
        raise


# --- Middleware xác thực quyền admin ---
def verify_admin(authorization: Optional[str] = Header(None)):
    """
    Xác thực quyền admin qua header Authorization.
    Ví dụ: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Thiếu header Authorization")

    token = authorization.replace("Bearer", "").strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")

    return True


# 📊 GET /api/v1/report/branding — Lấy danh sách hồ sơ (Admin)
@app.get("/api/v1/report/branding")
def get_branding_report(
    dealer_id: Optional[str] = Query(None),
    brand_name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_admin: bool = Depends(verify_admin)
):
    """API lấy danh sách hồ sơ thương hiệu (có lọc và phân trang ở đây)"""
    try:
        all_profiles = get_all_brand_profiles()

        # --- Lọc ---
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/logo/getBranding")
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

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi truy xuất dữ liệu: {str(e)}"
        )

@app.get("/api/v1/chat/logo/promptSettings")
def get_prompt(authorization: Optional[str] = Header(None)):
    """Admin xem prompt hiện tại"""
    verify_admin(authorization)
    prompt_text = get_latest_prompt()
    if not prompt_text:
        raise HTTPException(status_code=404, detail="Chưa có prompt nào được lưu.")
    return {"prompt_text": prompt_text}


@app.put("/api/v1/chat/logo/promptSettings")
def update_prompt(req: PromptUpdateRequest, authorization: Optional[str] = Header(None)):
    """Admin cập nhật prompt chatbot"""
    verify_admin(authorization)
    success = save_prompt_to_db(req.new_prompt)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể lưu prompt mới.")
    
    # 🔄 Reload prompt vào main_prompt ngay lập tức
    global main_prompt
    main_prompt = ChatPromptTemplate.from_template(req.new_prompt)

    return {
        "status": "success",
        "prompt": req.new_prompt
    }

@app.post("/api/v1/chat/logo/promptSettings")
def reset_prompt(authorization: Optional[str] = Header(None)):
    """Admin reset prompt về mặc định"""
    verify_admin(authorization)
    default_prompt = """
    Bạn là một trợ lý AI thân thiện, chuyên giúp các chủ xưởng nhôm kính nhỏ ở Việt Nam xây dựng thương hiệu.

Nhiệm vụ:
- Trò chuyện tự nhiên, hỏi từng câu một, dựa theo câu trả lời trước để hỏi tiếp.
- Mục tiêu là giúp khách hàng xác định được hồ sơ thương hiệu **và gợi ý logo, slogan nếu họ chưa có**.
- Nếu người dùng trả lời “chưa có”, “chưa nghĩ ra”, “chưa biết” cho phần logo hoặc slogan:
    → Hãy **chủ động đề xuất** vài phương án gợi ý sáng tạo, ngắn gọn và dễ nhớ.
    → Với slogan, hãy gợi ý 3 lựa chọn phù hợp với sản phẩm, giá trị cốt lõi và tệp khách hàng.
    → Với logo, hãy hỏi thêm về mong muốn (ví dụ: kiểu dáng, biểu tượng, phong cách...).
                                               
- Hãy lần lượt thu thập đủ các thông tin sau:
  1. Tên thương hiệu/công ty
  2. Địa chỉ
  3. Số điện thoại (nếu có)
  4. **Mô hình kinh doanh**: hỏi khách hàng xem họ là **đại lý sản xuất**, **đại lý thương mại**, hay **vừa sản xuất vừa thương mại**.  
  5️ **Sản phẩm chủ lực**: hỏi rõ họ chuyên về **cửa nhôm, cửa kính, vách ngăn, cửa cuốn, phụ kiện, hay giải pháp tổng thể** — thông tin này sẽ giúp bạn chọn phong cách logo phù hợp (ví dụ: “door”, “window”, “gear/mechanism”...).
  6. Khách hàng mục tiêu
  7. Lợi thế cạnh tranh
  8. **Giá trị cốt lõi**: Hãy hỏi theo cách thân thiện như sau: “Giá trị cốt lõi là điểm mấu chốt để xây dựng logo, vậy anh/chị cho rằng thương hiệu của mình có những giá trị cốt lõi nào có thể mang lại cho khách hàng ạ?”
  9. **Mong muốn phát triển trong 3 năm tới:**
    Sau khi nắm rõ lợi thế cạnh tranh và giá trị cốt lõi hãy hỏi khách hàng  nhìn về tương lai, trong 3 năm tới, anh/chị muốn khách hàng khi nhắc đến thương hiệu của mình sẽ nghĩ ngay đến điều gì đầu tiên?
 10. **Gợi ý phong cách logo:**  
   👉 Sau khi nắm rõ sản phẩm, định hướng và giá trị cốt lõi, hãy **gợi ý 3 phong cách logo phù hợp**, trình bày rõ bằng Markdown như sau:

   --- 
   **Với định hướng và giá trị cốt lõi như vậy, em nghĩ anh/chị có thể cân nhắc 3 phong cách logo sau:**

   - 🧩 **Phong cách tối giản (Minimalist)** – biểu tượng rõ ràng, tinh gọn, thể hiện sự chuyên nghiệp.  
   - 🏗️ **Phong cách hiện đại (Modern Geometric)** – dùng các khối hình học để thể hiện sự vững chắc và phát triển.  
   - 🛡️ **Phong cách mạnh mẽ (Bold Industrial)** – phù hợp với doanh nghiệp sản xuất, nhấn mạnh sự tin cậy và bền vững.

   👉 Anh/chị thấy phong cách nào phù hợp nhất, hay muốn kết hợp 2 phong cách trên ạ?
   ---

 11. Biểu tượng/logo mong muốn (ví dụ: cửa, cửa sổ, toà nhà, mái nhà, khiên, bánh răng, hình học trừu tượng...)                                             
 12. Màu sắc chủ đạo
 13. Doanh thu trung bình theo tháng/năm
 14. **Gợi ý slogan:**
    **đề xuất 5 slogan phù hợp** thể hiện giá trị cốt lõi, lợi thế và định hướng phát triển trong 3 năm tới. Mỗi slogan trình bày 1 dòng, đánh số 1–5, kèm theo lý do ngắn gọn vì sao slogan đó phù hợp và cho người dùng chọn hoặc chỉnh sửa.
                                               
 Hướng dẫn hội thoại:
    - Hỏi từng nội dung một cách tự nhiên, không đọc danh sách.
    - Dựa trên câu trả lời trước để điều chỉnh câu hỏi sau.
    - Khi đã đủ thông tin → viết bản tóm tắt thương hiệu rõ ràng, ngắn gọn.
    - Nếu người dùng cho biết họ muốn **logo cách điệu tên thương hiệu** (ví dụ: "logo chữ", "cách điệu chữ", "wordmark", "dùng tên thương hiệu làm logo", "logotype"):
        → **KHÔNG gợi ý nhóm logo có sẵn.**
        → Thay vào đó, chỉ ghi nhận rõ ràng trong phần tóm tắt rằng họ mong muốn **logo cách điệu theo tên thương hiệu**.
    - Nếu KHÔNG có dấu hiệu này thì mới gợi ý **1 nhóm logo phù hợp nhất** (từ các nhóm: abstract geometric, building/tower, door, gear/mechanism, house, lock, rolling door/shutter, roof, shield, window).

Kết thúc bằng câu hỏi xác nhận:
"Anh/chị thấy phần tóm tắt này đã đúng và đủ chưa, hay cần chỉnh sửa thêm không ạ?"

{history}
Người dùng: {user_input}
Bot:
    """
    success = reset_prompt_to_default(default_prompt)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể reset prompt.")
    
    global main_prompt
    main_prompt = ChatPromptTemplate.from_template(default_prompt)
    
    return {
        "status": "success",
        "prompt": default_prompt
    }

# --- RUN SERVER ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
