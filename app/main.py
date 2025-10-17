from fastapi import FastAPI
import uvicorn
from app.api.v1.chat_router import router as chat_router
from app.api.v1.assets_router import router as assets_router
from app.api.v1.auth_router import router as auth_router
from app.api.v1.report_router import router as report_router
from app.api.v1.branding_router import router as branding_router
from app.api.v1.prompt_router import router as prompt_router
app = FastAPI(title="AI Brand Assistant API v1")

# Đăng ký router
app.include_router(chat_router, tags=["Chatbot"])
app.include_router(assets_router, tags=["Assets"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(report_router, tags=["Report"])
app.include_router(branding_router, tags=["Branding"])
app.include_router(prompt_router, tags=["Prompt Settings"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
