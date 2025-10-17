from datetime import datetime, timedelta
import uuid
from app.core.llm import memory  # import memory từ core.llm

sessions = {}  # {session_id: {"user_id": str, "expires_at": datetime, "memory": memory_object}}
SESSION_EXPIRATION_HOURS = 4

def get_or_create_session(user_id: str):
    """Tạo hoặc lấy session đang hoạt động cho user"""
    now = datetime.utcnow()

    # Tìm session còn hạn cho user
    for sid, sess in sessions.items():
        if sess.get("user_id") == user_id and sess.get("expires_at") > now:
            return sid, sess

    # Nếu không có session hợp lệ → tạo mới
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "user_id": user_id,
        "expires_at": now + timedelta(hours=SESSION_EXPIRATION_HOURS),
        "memory": memory
    }

    print(f"🆕 New session created for user {user_id}: {session_id}")
    return session_id, sessions[session_id]
