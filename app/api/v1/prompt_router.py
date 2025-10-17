from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate

from app.core.auth import verify_admin
from app.models.chat_models import PromptUpdateRequest
from app.database.crud import get_latest_prompt, save_prompt, reset_prompt

# Dùng chung với chatbot
from app.core.llm import main_prompt

router = APIRouter(prefix="/api/v1/chat/logo", tags=["Prompt Settings"])


# 🧠 LẤY PROMPT HIỆN TẠI
@router.get("/promptSettings")
def get_prompt(auth: bool = Depends(verify_admin)):
    """Admin xem prompt hiện tại"""
    # verify_admin(authorization)
    prompt_text = get_latest_prompt()
    if not prompt_text:
        raise HTTPException(status_code=404, detail="Chưa có prompt nào được lưu.")
    return {
        "status": "success",
        "prompt": prompt_text
    }


# ✏️ CẬP NHẬT PROMPT MỚI
@router.post("/promptSettings")
def update_prompt(req: PromptUpdateRequest, auth: bool = Depends(verify_admin)):
    """Admin cập nhật prompt chatbot"""
    # verify_admin(authorization)

    success = save_prompt(req.new_prompt)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể lưu prompt mới.")

    # 🔄 Cập nhật prompt trong bộ nhớ hiện tại
    global main_prompt
    main_prompt = ChatPromptTemplate.from_template(req.new_prompt)

    return {
        "status": "success",
        "prompt": req.new_prompt
    }


# 🔁 RESET PROMPT VỀ MẶC ĐỊNH
@router.get("/promptReset")
def reset_prompt_api(auth: bool = Depends(verify_admin)):
    """Admin reset prompt về mặc định"""
    # verify_admin(authorization)

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

    success = reset_prompt(default_prompt)
    if not success:
        raise HTTPException(status_code=500, detail="Không thể reset prompt.")

    global main_prompt
    main_prompt = ChatPromptTemplate.from_template(default_prompt)

    return {
        "status": "success",
        "prompt": default_prompt
    }
