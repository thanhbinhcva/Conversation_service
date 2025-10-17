# app/database/crud.py
from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from app.database.connection import users, logo_emblems, brand_profiles, chatbot_prompts

# --- USER ---
def create_user(username: str, password: str, role: str = "user"):
    if users.find_one({"username": username}):
        return None

    hashed_pw = generate_password_hash(password)
    user = {
        "username": username,
        "password": hashed_pw,
        "role": role,
        "created_at": datetime.utcnow()
    }
    result = users.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user


def find_user_by_username(username: str):
    user = users.find_one({"username": username})
    if user:
        user["_id"] = str(user["_id"])
    return user


def verify_password(plain_pw: str, hashed_pw: str):
    return check_password_hash(hashed_pw, plain_pw)


# --- LOGO EMBLEMS ---
def save_logo_emblem(data: dict):
    try:
        result = logo_emblems.insert_one(data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Error saving emblem: {e}")
        return None


def update_logo_emblem_in_db(emblem_id: str, category: str, variants: list):
    try:
        if not ObjectId.is_valid(emblem_id):
            return False

        result = logo_emblems.update_one(
            {"_id": ObjectId(emblem_id)},
            {"$set": {"category": category, "variant": variants}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"❌ Error updating emblem: {e}")
        return False


def delete_logo_emblem_from_db(emblem_id: str):
    try:
        if not ObjectId.is_valid(emblem_id):
            return False
        result = logo_emblems.delete_one({"_id": ObjectId(emblem_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"❌ Error deleting emblem: {e}")
        return False


# --- BRAND PROFILE ---
def save_brand_profile(data: dict):
    try:
        result = brand_profiles.insert_one(data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Error saving brand_profile: {e}")
        return None

def get_brand_profile_by_session(session_id: str):
    result = brand_profiles.find_one({"session_id": session_id})
    if not result:
        return None
    result["_id"] = str(result["_id"])
    return result


def get_all_brand_profiles():
    cursor = brand_profiles.find().sort("_id", -1)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


# --- PROMPT ---
def get_latest_prompt():
    result = chatbot_prompts.find_one(sort=[("_id", -1)])
    return result.get("prompt_text") if result else None


def save_prompt(prompt_text: str):
    doc = {"prompt_text": prompt_text, "updated_at": datetime.utcnow()}
    chatbot_prompts.insert_one(doc)
    return True


def reset_prompt(default_text: str):
    doc = {"prompt_text": default_text, "reset_at": datetime.utcnow(), "is_default": True}
    chatbot_prompts.insert_one(doc)
    return True
