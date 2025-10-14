import os
import json
import uuid
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from logo_generator import generate_logo_with_ai
from database import save_prompt_to_db, get_latest_prompt
# 1. Load API key
load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")

# 2. Khởi tạo Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.4,
    google_api_key=google_api_key
)

# 3. Bộ nhớ hội thoại
memory = ConversationBufferMemory(memory_key="history", input_key="user_input")

# 4. Prompt tổng hợp (gom hết các stages)
default_prompt_text = """
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

prompt_from_db = get_latest_prompt()
if not prompt_from_db:
    print("⚠️ Không tìm thấy prompt trong DB — sử dụng prompt mặc định.")
    save_prompt_to_db(default_prompt_text)
    prompt_from_db = default_prompt_text
else:
    print("✅ Đã tải prompt động từ MongoDB.")

# 5. Tạo Prompt & Chain
main_prompt = ChatPromptTemplate.from_template(prompt_from_db)
main_chain = LLMChain(llm=llm, prompt=main_prompt, memory=memory, verbose=False)

# 6. Hàm trích xuất JSON
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
    "business_model: "",
    "main_services": ["string"],
    "product_portfolio": [
        {{
            "product": "string",
            "rate": "float hoặc string"
        }}
    ],
    "target_customers": ["string"],
    "competitive_advantage": ["string"],
    "core_values": ["string"],
    "slogan": "string",
    "future_vision": ["string"],
    "logo_style": ["string"],
    "main_color": ["string"],
    "revenue": ["string"]
    "logo_shape": [],                                          
}}

Đoạn hội thoại:
{conversation}
""")
    extract_chain = LLMChain(llm=llm, prompt=extract_prompt, verbose=False)
    response = extract_chain.invoke({"conversation": conversation, "session_id": session_id})
    raw_text = response.get("text", "").strip()

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

# 7. Danh sách thư mục logo
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

# 8. Gợi ý label logo
def recommend_logo(conversation: str):
    prompt = ChatPromptTemplate.from_template("""
Bạn là một chuyên gia thương hiệu.
Dựa trên toàn bộ đoạn hội thoại sau, hãy chọn duy nhất 1 nhóm logo phù hợp nhất.

Danh sách nhóm logo có sẵn:
- Abstract geometric
- Building/Tower
- Door
- Gear/mechanism
- House
- Lock/security
- Rolling door/shutter
- Roof
- Shield
- Window

⚠️ Chỉ trả về JSON hợp lệ theo đúng cấu trúc:
{{
  "recommended_category": "tên nhóm logo",
  "reason": "giải thích ngắn gọn"
}}

Đoạn hội thoại:
{conversation}
""")

    chain = LLMChain(llm=llm, prompt=prompt, verbose=False)
    response = chain.invoke({"conversation": conversation})

    text = response.get("text", "").strip()

    # Bóc JSON bằng regex

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("❌ recommend_logo: Model không trả về JSON.\nKết quả:", text)

    result = json.loads(match.group())

    # Thêm folder path
    folder_path = logo_folders.get(result["recommended_category"], "logos/abstract_geometric/")
    result["folder_path"] = folder_path
    return result

    
# 7. Lưu JSON
def save_brand_profile(data, filename="brand_profile.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Hồ sơ thương hiệu đã lưu vào {filename}")

# 🧠 Hàm nhận dạng linh hoạt mong muốn "cách điệu tên thương hiệu"
def wants_wordmark_logo(logo_shape_field):
    """
    Kiểm tra xem người dùng có muốn logo cách điệu tên thương hiệu không.
    Có thể nhận dạng qua nhiều cách diễn đạt khác nhau.
    """
    if not logo_shape_field:
        return False

    # Gộp tất cả text lại (nếu là list)
    if isinstance(logo_shape_field, list):
        combined = " ".join(logo_shape_field).lower()
    else:
        combined = str(logo_shape_field).lower()

    # Danh sách các từ khóa linh hoạt
    keywords = [
        "cách điệu", "cách điệu tên", "chữ cách điệu", "logo chữ", 
        "kiểu chữ", "wordmark", "text-only", "lettermark", 
        "logotype", "dạng chữ", "tên thương hiệu cách điệu", 
        "biểu tượng chữ"
    ]

    return any(keyword in combined for keyword in keywords)

# 8. Chạy hội thoại
def run_chatbot():
    print("🤖 Chatbot Gemini - Tư vấn thương hiệu\n")

    # Khởi động hội thoại
    user_input = "Xin chào"
    response = main_chain.invoke({"user_input": user_input})
    print("Bot:", response["text"])

    # Vòng lặp hội thoại
    while True:
        user_input = input("Bạn: ")
        response = main_chain.invoke({"user_input": user_input})
        print("Bot:", response["text"])

        # Nếu bot đã tóm tắt và hỏi xác nhận
        if "đúng và đủ" in response["text"].lower() or "chỉnh sửa" in response["text"].lower():
            break

    # Xử lý xác nhận
    while True:
        user_input = input("Bạn: ")
        if any(word in user_input.lower() for word in ["đúng", "đủ", "chính xác", "ok", "oke", "rồi"]):
            print("Bot: Tuyệt vời! Rất vui vì đã giúp anh/chị định hình thương hiệu. 🚀")
            final_summary = memory.load_memory_variables({})["history"]
            brand_profile = extract_info(final_summary)
            save_brand_profile(brand_profile)
            # Gợi ý label logo
            # Nếu logo_shape là "Cách điệu tên thương hiệu" → gọi AI sinh logo
            if wants_wordmark_logo(brand_profile.get("logo_shape", [])):
                print("\n🤖 Phát hiện yêu cầu tạo logo cách điệu tên thương hiệu...")
                ai_logo = generate_logo_with_ai(
                    brand_profile, 
                    google_api_key=google_api_key, 
                    output_path="generated_image.png"
                )
                if ai_logo:
                    print(f"🎨 Logo AI đã được tạo và lưu tại: {ai_logo}")
                else:
                    print("⚠️ Không thể tạo logo AI, vui lòng thử lại sau.")
            else:
                # Nếu không phải, gợi ý logo từ thư mục có sẵn
                logo_suggestion = recommend_logo(final_summary)
                print("\n🎨 Logo đề xuất cho thương hiệu của anh/chị:")
                print("👉 Nhóm logo:", logo_suggestion["recommended_category"])
                print("📌 Lý do:", logo_suggestion["reason"])
                print("📂 Folder:", logo_suggestion["folder_path"])
            break
        else:
            fix_prompt = ChatPromptTemplate.from_template("""
{history}
Khách hàng chưa hài lòng với bản tóm tắt, họ muốn chỉnh sửa: "{feedback}".
Hãy viết lại bản tóm tắt thương hiệu đầy đủ và chính xác hơn, sau đó hỏi lại họ xác nhận.
""")
            fix_chain = LLMChain(llm=llm, prompt=fix_prompt, memory=memory, verbose=False)
            response = fix_chain.invoke({"user_input": user_input, "feedback": user_input})
            print("Bot:", response["text"])

if __name__ == "__main__":
    run_chatbot()
