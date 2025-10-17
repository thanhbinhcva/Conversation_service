from fastapi import APIRouter, HTTPException
from app.models.chat_models import ChatRequest, ChatResponse
from app.services.chatbot_service import should_finalize, auto_finalize
from app.services.session import get_or_create_session
from app.core.llm import main_chain

router = APIRouter(prefix="/api/v1/logo", tags=["Chatbot"])


@router.post("/chat", response_model=ChatResponse)
def chat_with_bot(req: ChatRequest):
    """ 
    Endpoint chính: /api/v1/logo/chat
    - Nhận {userID, user_input}
    - Tự tạo / tái sử dụng sessionID (hết hạn sau 4h)
    - Tự động finalize nếu người dùng xác nhận 'đúng và đủ'
    """
    try:
        # 1️⃣ Lấy hoặc tạo session
        session_id, sess_data = get_or_create_session(req.userID)
        sess_memory = sess_data["memory"]

        # 2️⃣ Chatbot phản hồi
        response = main_chain.invoke({"user_input": req.user_input})
        bot_reply = response.get("text", "").strip()

        # 3️⃣ Lấy lịch sử hội thoại
        history_data = sess_memory.load_memory_variables({}).get("history", "")

        # 4️⃣ Kiểm tra xem có finalize không
        finalized = should_finalize(history_data, req.user_input)
        if finalized:
            finalized_result = auto_finalize(sess_memory)
            if finalized_result and finalized_result.get("brand_profile"):
                bot_reply = (
                    "✅ Hồ sơ đã được tổng hợp và lưu thành công vào hệ thống. 🚀"
                )
            else:
                bot_reply = (
                    "⚠️ Không thể lưu hồ sơ vì chưa đủ dữ liệu. Vui lòng tiếp tục trò chuyện thêm nhé!"
                )

        # 5️⃣ Trả kết quả cho frontend
        return ChatResponse(
            message=bot_reply,
            finished=finalized,
            receiverID="chatbot_brand_assistant",
            sessionID=session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
