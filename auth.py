from fastapi import HTTPException, Request
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USER")
ADMIN_PASSWORD = os.getenv("ADMIN_PASS")

def verify_admin(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def require_admin(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(status_code=401, detail="Unauthorized")
