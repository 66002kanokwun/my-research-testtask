from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import storage
from .config import ROOT
from .models import Task
from .pipeline import run_pipeline

app = FastAPI(title="E2E AI Code Quality Dashboard")
TASKS_DIR = ROOT / "tasks"


class RunRequest(BaseModel):
    task_file: str = "todo-api.yaml"
    provider: str | None = None
    model: str | None = None


@app.get("/")
def index():
    return FileResponse(ROOT / "dashboard" / "index.html")


@app.get("/api/runs")
def runs():
    return storage.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    r = storage.get_run(run_id)
    if not r:
        raise HTTPException(404, "run not found")
    return r


@app.get("/api/tasks")
def tasks():
    return [{"file": p.name, "name": Task.load(p).name} for p in sorted(TASKS_DIR.glob("*.yaml"))]


@app.post("/api/runs")
def start_run(req: RunRequest, bg: BackgroundTasks):
    path = (TASKS_DIR / Path(req.task_file).name)
    if not path.exists():
        raise HTTPException(404, "task file not found")
    task = Task.load(path)
    from .config import get_settings

    s = get_settings()
    provider, model = req.provider or s.ai_provider, req.model or s.ai_model
    run_id = storage.create_run(task.id, task.name, provider, model)
    bg.add_task(run_pipeline, str(path), provider, model, run_id)
    return {"run_id": run_id}
