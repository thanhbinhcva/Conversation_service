import json, re, uuid
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import llm, memory, main_chain
# from utils.wordmark_detector import wants_wordmark_logo
from app.services.logo_service import generate_logo_with_ai, recommend_logo
from app.database.crud import save_brand_profile
from datetime import datetime
import os
# --- Hàm trích xuất JSON ---
def extract_info(conversation: str):
    session_id = str(uuid.uuid4())[:8]

    extract_prompt = ChatPromptTemplate.from_template("""
Bạn là hệ thống trích xuất dữ liệu. 
Hãy phân tích đoạn hội thoại sau và xuất ra JSON theo đúng cấu trúc dưới đây.
Chỉ trả về JSON hợp lệ, không thêm text ngoài JSON.

{{
    "session_id": "{session_id}",
    "dealer_id": "string",
    "brand_name_full": "string",
    "location": {{
        "number": "string",
        "street": "string",
        "ward": "string",
        "city": "string"
    }},
    "business_model": "string",
    "main_services": ["string"],
    "product_portfolio": [
        {{
            "product": "string",
            "rate": "string"
        }}
    ],
    "target_customers": ["string"],
    "competitive_advantage": ["string"],
    "core_values": ["string"],
    "slogan": "string",
    "future_vision": ["string"],
    "logo_style": ["string"],
    "main_color": ["string"],
    "revenue": ["string"],
    "logo_shape": ["string"]
}}

Đoạn hội thoại:
{conversation}
""")

    chain = LLMChain(llm=llm, prompt=extract_prompt, verbose=False)
    response = chain.invoke({"conversation": conversation, "session_id": session_id})
    raw_text = response.get("text", "").strip()

    # --- Debug log để xem mô hình trả về gì ---
    print("\n=== RAW MODEL OUTPUT (extract_info) ===")
    print(raw_text)
    print("=======================================\n")

    # --- Parse JSON ---
    try:
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise ValueError("Không tìm thấy JSON hợp lệ.")
        json_data = json.loads(match.group())
    except Exception as e:
        print(f"⚠️ Lỗi parse JSON: {e}")
        json_data = {"session_id": session_id, "raw_output": raw_text}

    # --- Chuẩn hóa dữ liệu ---
    json_data.setdefault("session_id", session_id)
    json_data.setdefault("location", {
        "number": "",
        "street": "",
        "ward": "",
        "city": ""
    })
    json_data.setdefault("main_services", [])
    json_data.setdefault("product_portfolio", [])
    json_data.setdefault("target_customers", [])
    json_data.setdefault("competitive_advantage", [])
    json_data.setdefault("core_values", [])
    json_data.setdefault("future_vision", [])
    json_data.setdefault("logo_style", [])
    json_data.setdefault("main_color", [])
    json_data.setdefault("revenue", [])
    return json_data

logo_folders = {
    "abstract geometric": "logos/abstract_geometric/",
    "building/tower": "logos/building_tower/",
    "door": "logos/door/",
    "gear/mechanism": "logos/gear/",
    "house": "logos/house/",
    "lock": "logos/lock/",
    "rolling door/shutter": "logos/rolling_door/",
    "roof": "logos/roof/",
    "shield": "logos/shield/",
    "window": "logos/window/"
}

# def save_brand_profile(data, filename="brand_profile.json"):
#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)

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

# --- FINALIZE LOGIC ---
def auto_finalize(sess_memory):
    """Tổng hợp thông tin & sinh logo"""
    try:
        final_summary = sess_memory.load_memory_variables({}).get("history", "")
        if not final_summary:
            print("⚠️ Không có dữ liệu hội thoại để tổng hợp.")
            return None

        print("\n📜 FINAL SUMMARY INPUT:")
        print(final_summary[:1000], "...")  # In 1000 ký tự đầu để kiểm tra
        print("=======================================")

        # Trích xuất dữ liệu thương hiệu
        brand_profile = extract_info(final_summary)
        brand_profile["created_at"] = datetime.utcnow().isoformat()

        # Lưu vào MongoDB
        inserted_id = save_brand_profile(brand_profile)
        if inserted_id:
            brand_profile["_id"] = str(inserted_id)
            print(f"✅ Brand profile đã lưu MongoDB với ID: {inserted_id}")
        else:
            print("⚠️ Không thể lưu brand_profile vào DB")

        # Sinh logo gợi ý
        logo_shape_text = " ".join(brand_profile.get("logo_shape", [])).lower()
        if any(keyword in logo_shape_text for keyword in [
            "cách điệu", "tên thương hiệu", "wordmark", "logo chữ", "logotype"
        ]):
            path = generate_logo_with_ai(
                brand_profile,
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                output_path="generated_logo.png"
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

