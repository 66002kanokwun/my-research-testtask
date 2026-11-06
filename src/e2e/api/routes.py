from pathlib import Path
from fastapi import BackgroundTasks, APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import ROOT, get_settings
from ..core.models import Task
from ..core.pipeline import run_pipeline
from ..integrations import storage
from ..services.run_service import create_new_run
from .schemas import RunRequest

router = APIRouter()
TASKS_DIR = ROOT / "tasks"
DASHBOARD_DIR = ROOT / "dashboard"

# ---------------------------------------------------------
# 1. Routes
# ---------------------------------------------------------
@router.get("/")
def index():
    return FileResponse(DASHBOARD_DIR / "index.html")


@router.get("/api/runs")
def runs():
    return storage.list_runs()


@router.get("/api/runs/{run_id}", responses={404: {"description": "Run not found"}})
def run_detail(run_id: int):
    r = storage.get_run(run_id)
    if not r:
        raise HTTPException(404, "run not found")
    return r


@router.get("/api/tasks")
def tasks():
    """ค้นหาไฟล์ Task หลักทั้งหมด (ตัดไฟล์ acceptance/base ออก)"""
    task_files = [
        p for p in TASKS_DIR.rglob("*.yaml") 
        if p.name.endswith("-api.yaml") or p.name == "api.yaml"
    ]
    
    result = []
    for p in sorted(task_files):
        try:
            t = Task.load(p)
            result.append({
                "file": str(p.relative_to(TASKS_DIR)).replace("\\", "/"), 
                "name": t.name
            })
        except Exception as e:
            # ถ้าไฟล์ไหนพัง ให้ข้ามไป ไม่ทำให้ API ล่ม
            print(f"Warning: Skipping invalid task file {p.name}: {e}")
            continue
            
    return result


@router.post("/api/runs", responses={404: {"description": "Task file not found"}})
def start_run(req: RunRequest, bg: BackgroundTasks):
    path = TASKS_DIR / req.task_file
    if not path.exists():
        raise HTTPException(404, f"Task file not found: {req.task_file}")
    
    try:
        run_id = create_new_run(req.task_file, req.provider, req.model)
        bg.add_task(run_pipeline, str(path), req.provider, req.model, run_id)
        return {"run_id": run_id}
    except FileNotFoundError:
        raise HTTPException(404, "task file not found")