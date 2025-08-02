import os
from fastapi import FastAPI, Request, Form, HTTPException, Cookie, Path
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime, timedelta
from db import users_collection, history_collection
from auth import is_valid_admin

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse("/admin/login")

@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/admin/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not is_valid_admin(username, password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie(key="admin_user", value=username, httponly=True)
    return response

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, admin_user: str = Cookie(None)):
    if not admin_user:
        return RedirectResponse("/admin/login")
    return templates.TemplateResponse("admin.html", {"request": request, "username": admin_user})

@app.get("/admin/users")
def get_users(admin_user: str = Cookie(None)):
    if not admin_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        now = datetime.utcnow()
        active_cutoff = now - timedelta(days=10)

        users = list(users_collection.find({}, {"_id": 0}))
        total_users = len(users)
        active_users = sum(1 for u in users if u.get("last_active") and u["last_active"] >= active_cutoff)

        for user in users:
            # Get last user_message from history
            last_chat = history_collection.find_one(
                {"username": user["username"], "user_message": {"$ne": "[Admin]"}},
                sort=[("timestamp", -1)]
            )
            user["last_message"] = last_chat["user_message"] if last_chat else "(no messages)"

        sorted_users = sorted(users, key=lambda u: u.get("last_active", datetime.min), reverse=True)
        return {"total_users": total_users, "active_users": active_users, "users": sorted_users}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/admin/chat-history")
def get_chat_history(username: str, admin_user: str = Cookie(None)):
    if not admin_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        raw_history = list(history_collection.find({"username": username}).sort("timestamp", 1))
        formatted = [
            {
                "sender": "user" if h.get("user_message") != "[Admin]" else "admin",
                "message": h.get("user_message") if h.get("user_message") != "[Admin]" else h.get("bot_response", ""),
                "timestamp": h.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if h.get("timestamp") else "N/A"
            } for h in raw_history
        ]
        return {"history": formatted}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/admin/send-message")
def send_admin_message(username: str = Form(...), message: str = Form(...), admin_user: str = Cookie(None)):
    if not admin_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        history_collection.insert_one({
            "username": username,
            "timestamp": datetime.utcnow(),
            "user_message": "[Admin]",
            "bot_response": message
        })
        return {"status": "Message sent"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/admin/toggle-ai")
def toggle_ai(username: str = Form(...), admin_user: str = Cookie(None)):
    if not admin_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        user = users_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        new_status = not user.get("ai_enabled", True)
        users_collection.update_one({"username": username}, {"$set": {"ai_enabled": new_status}})
        return {"username": username, "ai_enabled": new_status}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/admin/chat-history-page/{username}", response_class=HTMLResponse)
def chat_history_page(request: Request, username: str = Path(...)):
    try:
        raw_history = list(history_collection.find({"username": username}).sort("timestamp", 1))
        formatted = []
        for h in raw_history:
            ts = h.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if h.get("timestamp") else "N/A"

            # Add user message
            if h.get("user_message") and h.get("user_message") != "[Admin]":
                formatted.append({
                    "sender": "user",
                    "message": h["user_message"],
                    "timestamp": ts
                })

            # Add bot response
            if h.get("bot_response"):
                formatted.append({
                    "sender": "bot",
                    "message": h["bot_response"],
                    "timestamp": ts
                })

            # Admin message (stored as bot_response when user_message is "[Admin]")
            if h.get("user_message") == "[Admin]":
                formatted.append({
                    "sender": "admin",
                    "message": h.get("bot_response", ""),
                    "timestamp": ts
                })

        return templates.TemplateResponse("chat_history.html", {"request": request, "username": username, "history": formatted})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})