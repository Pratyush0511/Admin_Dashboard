from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

if not MONGO_URL or not MONGO_DB_NAME:
    raise RuntimeError("❌ MONGO_URL or MONGO_DB_NAME not set in .env")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB_NAME]

users_collection = db["users"]
history_collection = db["history"]
