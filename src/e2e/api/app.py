from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import router
from ..config import ROOT

app = FastAPI(title="E2E AI Code Quality Dashboard")

# ชี้ไปที่โฟลเดอร์ static ที่เราเพิ่งสร้าง
STATIC_DIR = ROOT / "dashboard" / "static"

# Mount ให้เข้าถึงผ่าน URL /static/...
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(router)