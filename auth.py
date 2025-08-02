import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_USERS = os.getenv("ADMIN_USERS")
ADMIN_PASS = os.getenv("ADMIN_PASS")

if not ADMIN_USERS or not ADMIN_PASS:
    raise RuntimeError("❌ ADMIN_USERS or ADMIN_PASS not set in .env")

ADMIN_USERS = [u.strip() for u in ADMIN_USERS.split(",")]

def is_valid_admin(username: str, password: str) -> bool:
    return username in ADMIN_USERS and password == ADMIN_PASS
