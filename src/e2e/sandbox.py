"""เขียนไฟล์ลง workspace และ (optional) รันเทสต์ใน Docker"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import GeneratedFile


def safe_join(base: Path, rel: str) -> Path:
    """กัน path traversal จาก output ของ AI"""
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError(f"unsafe path from model: {rel}")
    return target


def write_workspace(base: Path, files: list[GeneratedFile]) -> Path:
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    for f in files:
        target = safe_join(base, f.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.content, encoding="utf-8")
    return base


def run_tests_in_docker(workspace: Path, image: str, command: str, timeout: int = 600) -> dict:
    """โค้ดจาก AI ไม่ควรรันบนเครื่องตรงๆ จึงรันใน container"""
    cmd = ["docker", "run", "--rm", "-v", f"{workspace.resolve()}:/work", "-w", "/work", image, "sh", "-c", command]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"passed": False, "output": f"{type(e).__name__}: {e}"}
    return {"passed": p.returncode == 0, "output": (p.stdout + p.stderr)[-4000:]}
