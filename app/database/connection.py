# app/database/connection.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "brand_assistant")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Các collection
brand_profiles = db["brand_profiles"]
chatbot_prompts = db["chatbot_prompts"]
logo_emblems = db["logo_emblems"]
users = db["users"]
