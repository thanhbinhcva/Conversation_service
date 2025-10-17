from pydantic import BaseModel

# --- MODELS ---
class ChatRequest(BaseModel):
    userID: str
    user_input: str


class ChatResponse(BaseModel):
    message: str
    finished: bool
    receiverID: str
    sessionID: str

class PromptUpdateRequest(BaseModel):
    new_prompt: str