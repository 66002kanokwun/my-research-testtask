"""ขั้นตอนที่ 3: สแกนด้วย SonarQube และดึง metrics"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

import requests

from .config import Settings

RATING = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}
RATING_METRICS = {"reliability_rating", "security_rating", "sqale_rating"}


def project_key(task_id: str, model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "-", f"e2e-{task_id}-{model}")


def run_scanner(workspace: Path, key: str, s: Settings, extra: dict, version: str) -> None:
    props = {
        "sonar.projectKey": key,
        "sonar.projectName": key,
        "sonar.projectVersion": version,
        "sonar.sources": "app" if (workspace / "app").exists() else ".",
        "sonar.token": s.sonar_token,
        **{k: str(v) for k, v in extra.items()},
    }
    if s.scanner_mode == "docker":
        props["sonar.host.url"] = s.scanner_host_url
        args = [a for k, v in props.items() for a in (f"-D{k}={v}",)]
        cmd = ["docker", "run", "--rm", "-v", f"{workspace.resolve()}:/usr/src", "sonarsource/sonar-scanner-cli", *args]
    else:
        props["sonar.host.url"] = s.sonar_host_url
        binary = shutil.which(s.scanner_bin) or s.scanner_bin
        cmd = [binary, *[f"-D{k}={v}" for k, v in props.items()]]
    p = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"sonar-scanner failed:\n{(p.stdout + p.stderr)[-3000:]}")


def _auth(s: Settings):
    return (s.sonar_token, "")


def wait_for_analysis(workspace: Path, s: Settings, timeout: int = 300) -> None:
    report = workspace / ".scannerwork" / "report-task.txt"
    if not report.exists():
        return
    kv = dict(line.split("=", 1) for line in report.read_text().splitlines() if "=" in line)
    url = kv.get("ceTaskUrl")
    if not url:
        return
    if s.scanner_mode == "docker":  # URL ที่ scanner เห็นอาจต่างจากที่ host เห็น
        url = url.replace(s.scanner_host_url, s.sonar_host_url)
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = requests.get(url, auth=_auth(s), timeout=30).json()["task"]
        if task["status"] == "SUCCESS":
            return
        if task["status"] in ("FAILED", "CANCELED"):
            raise RuntimeError(f"Sonar analysis {task['status']}")
        time.sleep(2)
    raise TimeoutError("Sonar analysis timeout")


def fetch_measures(key: str, metrics: list[str], s: Settings) -> dict:
    r = requests.get(
        f"{s.sonar_host_url}/api/measures/component",
        params={"component": key, "metricKeys": ",".join(metrics)},
        auth=_auth(s),
        timeout=30,
    )
    r.raise_for_status()
    out: dict = {m: None for m in metrics}
    for m in r.json()["component"]["measures"]:
        v = m.get("value")
        if m["metric"] in RATING_METRICS and v is not None:
            v = RATING.get(v, v)
        out[m["metric"]] = v
    return out


def fetch_quality_gate(key: str, s: Settings) -> str:
    r = requests.get(
        f"{s.sonar_host_url}/api/qualitygates/project_status",
        params={"projectKey": key},
        auth=_auth(s),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["projectStatus"]["status"]  # OK | ERROR | NONE
