from pathlib import Path
from ..core.models import Task
from ..integrations import storage
from ..config import ROOT, get_settings


def create_new_run(task_file: str, provider: str | None = None, model: str | None = None) -> int:
    # task_file ที่ส่งมาจะเป็น relative path เช่น "todo-react-test/todo-api.yaml"
    path = ROOT / "tasks" / task_file
    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")
    
    task = Task.load(path)
    
    s = get_settings()
    final_provider = provider or s.ai_provider
    final_model = model or s.ai_model

    run_id = storage.create_run(task.id, task.name, final_provider, final_model)
    return run_id