import os
import json
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tiktok-bot")

app = FastAPI(title="TikTok Bot - Complete Starter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENT_KEY = os.getenv("CLIENT_KEY", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
STORAGE_FILE = os.getenv("STORAGE_FILE", "tokens.json")

if not os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "w") as f:
        json.dump({"accounts": {}}, f)

def read_storage():
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def write_storage(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_token(tiktok_user_id: str, access_token: str, refresh_token: Optional[str]=None):
    data = read_storage()
    data["accounts"][tiktok_user_id] = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
    write_storage(data)
    logger.info(f"Saved token for {tiktok_user_id}")

def get_any_token():
    data = read_storage()
    accounts = data.get("accounts", {})
    if not accounts:
        return None, None
    for k,v in accounts.items():
        return k, v.get("access_token")
    return None, None

@app.get("/")
def home():
    return {"status": "ok", "message": "TikTok Bot ready"}

@app.get("/login_tiktok")
def login_tiktok():
    if not CLIENT_KEY or not REDIRECT_URI:
        return JSONResponse({"ok": False, "error": "CLIENT_KEY or REDIRECT_URI not set in env"}, status_code=400)
    scope = "user.info.basic,video.upload,video.publish"
    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/?"
        f"client_key={CLIENT_KEY}&response_type=code&scope={scope}&redirect_uri={REDIRECT_URI}"
    )
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(code: str = None):
    if not code:
        return JSONResponse({"ok": False, "error": "missing code"}, status_code=400)
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
    resp = requests.post(token_url, data=data)
    try:
        body = resp.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid response from TikTok", "raw": resp.text}, status_code=500)
    access_token = body.get("data", {}).get("access_token") or body.get("access_token") or body.get("accessToken")
    open_id = body.get("data", {}).get("open_id") or body.get("open_id") or body.get("openId")
    refresh_token = None
    if body.get("data"):
        refresh_token = body.get("data").get("refresh_token") or body.get("refresh_token")
    if not access_token or not open_id:
        return JSONResponse({"ok": False, "error": "could not obtain access_token or open_id", "resp": body}, status_code=500)
    save_token(open_id, access_token, refresh_token)
    return JSONResponse({"ok": True, "message": "TikTok account connected", "open_id": open_id})

@app.post("/upload_video")
async def upload_video(file: UploadFile = File(...)):
    os.makedirs("videos", exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    dest = os.path.join("videos", filename)
    with open(dest, "wb") as f:
        contents = await file.read()
        f.write(contents)
    logger.info(f"Saved upload to {dest}")
    return {"ok": True, "path": dest, "filename": filename}

@app.post("/postar")
def postar(caption: str = Form(""), video_path: Optional[str] = Form(None)):
    open_id, access_token = get_any_token()
    if not access_token:
        return JSONResponse({"ok": False, "error": "no connected TikTok account"}, status_code=400)
    if not video_path or not os.path.exists(video_path):
        return JSONResponse({"ok": False, "error": "video_path missing or file not found"}, status_code=400)
    try:
        init_url = "https://open.tiktokapis.com/v2/video/upload/init/"
        headers = {"Authorization": f"Bearer {access_token}"}
        init_resp = requests.post(init_url, headers=headers).json()
        upload_url = init_resp.get("upload_url")
        if not upload_url:
            return JSONResponse({"ok": False, "error": "init failed", "resp": init_resp}, status_code=500)
        with open(video_path, "rb") as f:
            up = requests.put(upload_url, data=f)
            if up.status_code not in (200,201):
                return JSONResponse({"ok": False, "error": "upload failed", "status_code": up.status_code, "text": up.text}, status_code=500)
        publish_url = "https://open.tiktokapis.com/v2/video/create/"
        payload = {"video_id": init_resp.get("video_id"), "text": caption}
        pub = requests.post(publish_url, headers=headers, json=payload).json()
        return JSONResponse({"ok": True, "result": pub})
    except Exception as e:
        logger.exception("posting failed")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/status")
def status():
    open_id, token = get_any_token()
    return {"ok": True, "connected_account": open_id is not None}
