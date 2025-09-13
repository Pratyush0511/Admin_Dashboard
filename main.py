from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
from db import customers_collection, history_collection
from auth import verify_admin, require_admin
from datetime import datetime, timedelta

load_dotenv()  # Load .env variables

app = FastAPI()

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- Root redirect ---
@app.get("/")
def root():
    return RedirectResponse("/login")


# --- Login ---
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if verify_admin(username, password):
        request.session["admin"] = True
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# --- Dashboard ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    require_admin(request)

    # Total users
    total_users = customers_collection.count_documents({})

    # Active users (last 10 days)
    ten_days_ago = datetime.utcnow() - timedelta(days=10)
    active_users = customers_collection.count_documents({"last_active": {"$gte": ten_days_ago}})

    # Users with last chat
    users = list(customers_collection.find({}))
    for u in users:
        last_chat_doc = history_collection.find_one({"customer_key": u["key"]}, sort=[("timestamp", -1)])
        u["last_chat"] = last_chat_doc["user_message"] if last_chat_doc else ""

    # Sort users by last chat timestamp (latest first)
    def last_chat_time(u):
        last_chat_doc = history_collection.find_one({"customer_key": u["key"]}, sort=[("timestamp", -1)])
        if last_chat_doc:
            return last_chat_doc["timestamp"].timestamp()
        return 0

    users.sort(key=last_chat_time, reverse=True)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_users": total_users,
        "active_users": active_users,
        "users": users
    })


# --- User Chat History ---
@app.get("/chat/{user_key}", response_class=HTMLResponse)
def chat_history(request: Request, user_key: str):
    require_admin(request)
    user = customers_collection.find_one({"key": user_key})
    if not user:
        return HTMLResponse("User not found", status_code=404)

    chats = list(history_collection.find({"customer_key": user_key}).sort("timestamp", 1))

    return templates.TemplateResponse("chat_history.html", {
        "request": request,
        "user": user,
        "chats": chats
    })


# --- Toggle AI ---
@app.post("/toggle_ai/{user_key}")
def toggle_ai(user_key: str, enable: bool = Form(...)):
    result = customers_collection.update_one({"key": user_key}, {"$set": {"ai_enabled": enable}})
    if result.modified_count == 0:
        return JSONResponse({"status": "failed"}, status_code=400)
    return JSONResponse({"status": "success"})
