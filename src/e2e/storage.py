from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT, task_name TEXT, provider TEXT, model TEXT,
  status TEXT, step TEXT, error TEXT,
  started_at TEXT, finished_at TEXT,
  gen_seconds REAL, input_tokens INTEGER, output_tokens INTEGER,
  tests_passed INTEGER, quality_gate TEXT,
  metrics TEXT, sonar_url TEXT
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(get_settings().db_path)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_run(task_id: str, task_name: str, provider: str, model: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO runs(task_id,task_name,provider,model,status,step,started_at) VALUES(?,?,?,?,?,?,?)",
            (task_id, task_name, provider, model, "running", "queued", now()),
        )
        return cur.lastrowid


def update_run(run_id: int, **fields) -> None:
    if "metrics" in fields:
        fields["metrics"] = json.dumps(fields["metrics"])
    cols = ", ".join(f"{k}=?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE runs SET {cols} WHERE id=?", (*fields.values(), run_id))


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["metrics"] = json.loads(d["metrics"]) if d.get("metrics") else {}
    return d


def list_runs() -> list[dict]:
    with _conn() as c:
        return [_row(r) for r in c.execute("SELECT * FROM runs ORDER BY id DESC")]


def get_run(run_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return _row(r) if r else None
