from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

# --- Kết nối MongoDB ---
mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB", "brand_assistant")

client = MongoClient(mongo_uri)
db = client[mongo_db_name]
collection = db["brand_profiles"]
prompt_collection = db["chatbot_prompts"]

def save_to_mongo(data: dict):
    """Lưu brand_profile vào MongoDB"""
    try:
        result = collection.insert_one(data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Lỗi khi lưu MongoDB: {e}")
        return None


def get_brand_profile_by_session(session_id: str):
    """Lấy thông tin brand_profile từ MongoDB theo session_id"""
    try:
        result = collection.find_one({"session_id": session_id})
        if not result:
            return None
        result["_id"] = str(result["_id"])
        return result
    except Exception as e:
        print(f"❌ Lỗi khi lấy brand_profile theo session_id: {e}")
        return None


def get_all_brand_profiles():
    """Lấy toàn bộ hồ sơ thương hiệu từ MongoDB (chưa lọc, chưa phân trang)"""
    try:
        cursor = collection.find().sort("_id", -1)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        print(f"❌ Lỗi khi lấy danh sách brand_profiles: {e}")
        return []


def get_latest_prompt():
    """Lấy prompt mới nhất từ MongoDB"""
    try:
        result = prompt_collection.find_one(sort=[("_id", -1)])
        if result:
            return result["prompt_text"]
        return None
    except Exception as e:
        print(f"❌ Lỗi khi lấy prompt: {e}")
        return None


def save_prompt_to_db(prompt_text: str):
    """Lưu prompt mới vào MongoDB"""
    try:
        doc = {"prompt_text": prompt_text, "updated_at": datetime.utcnow()}
        prompt_collection.insert_one(doc)
        return True
    except Exception as e:
        print(f"❌ Lỗi khi lưu prompt: {e}")
        return False


def reset_prompt_to_default(default_text: str):
    """Reset prompt về mặc định"""
    try:
        doc = {"prompt_text": default_text, "reset_at": datetime.utcnow(), "is_default": True}
        prompt_collection.insert_one(doc)
        return True
    except Exception as e:
        print(f"❌ Lỗi khi reset prompt: {e}")
        return False