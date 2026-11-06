import pytest

from e2e.core.models import GeneratedFile, Task
from e2e.integrations.sandbox import safe_join, write_workspace
from e2e.integrations.sonar import project_key


def test_task_loads():
    t = Task.load("tasks/todo-api.yaml")
    assert t.id == "todo-react"
    assert "bugs" in t.metrics


def test_safe_join_blocks_traversal(tmp_path):
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../evil.py")


def test_write_workspace(tmp_path):
    ws = write_workspace(tmp_path / "w", [GeneratedFile("a/b.py", "x=1")])
    assert (ws / "a" / "b.py").read_text() == "x=1"


def test_project_key_sanitized():
    assert " " not in project_key("t", "claude sonnet/5")