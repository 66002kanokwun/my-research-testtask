from pydantic import BaseModel

class RunRequest(BaseModel):
    task_file: str = "todo-api.yaml"
    provider: str | None = None
    model: str | None = None