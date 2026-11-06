"""ขั้นตอนที่ 3: สแกนด้วย SonarQube และดึง metrics"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

import requests

from ..config import Settings
from ..utils.logger import logger

RATING = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}
RATING_METRICS = {"reliability_rating", "security_rating", "sqale_rating"}


def project_key(task_id: str, model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "-", f"e2e-{task_id}-{model}")


def _build_scanner_cmd(workspace: Path, key: str, s: Settings, extra: dict, version: str) -> list[str]:
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
        args = [f"-D{k}={v}" for k, v in props.items()]
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{workspace.resolve().as_posix()}:/usr/src",
            "sonarsource/sonar-scanner-cli",
            *args,
        ]
    else:
        props["sonar.host.url"] = s.sonar_host_url
        binary = shutil.which(s.scanner_bin) or s.scanner_bin
        cmd = [binary, *[f"-D{k}={v}" for k, v in props.items()]]
    return cmd


def _extract_ce_task_url(output: str) -> str | None:
    for line in output.splitlines():
        if "api/ce/task?id=" in line:
            idx = line.find("http")
            if idx != -1:
                return line[idx:].strip()
    return None


def run_scanner(workspace: Path, key: str, s: Settings, extra: dict, version: str) -> str | None:
    cmd = _build_scanner_cmd(workspace, key, s, extra, version)

    logger.info("\n=== SONAR CMD ===")
    safe_cmd = [c if not c.startswith("-Dsonar.token=") else "-Dsonar.token=***" for c in cmd]
    logger.info(" ".join(safe_cmd))
    logger.info("=================\n")

    p = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=900)

    logger.info("--- sonar-scanner stdout (3000 chars) ---")
    logger.info(p.stdout[-3000:])
    logger.info("--- sonar-scanner stderr (3000 chars) ---")
    logger.info(p.stderr[-3000:])
    logger.info(f"--- returncode: {p.returncode} ---\n")

    if p.returncode != 0:
        raise RuntimeError(f"sonar-scanner failed:\n{(p.stdout + p.stderr)[-3000:]}")

    ce_task_url = _extract_ce_task_url(p.stdout)

    if not ce_task_url:
        report = workspace / ".scannerwork" / "report-task.txt"
        if report.exists():
            kv = dict(line.split("=", 1) for line in report.read_text().splitlines() if "=" in line)
            ce_task_url = kv.get("ceTaskUrl")
            logger.info("[run_scanner] fallback: อ่าน ceTaskUrl จาก report-task.txt")

    if ce_task_url:
        logger.info(f"[run_scanner] ceTaskUrl = {ce_task_url}")
    else:
        logger.warning("[run_scanner] WARNING: ไม่พบ ceTaskUrl")

    return ce_task_url


def _auth(s: Settings):
    return (s.sonar_token, "")


# >>> แก้ไข: ลบพารามิเตอร์ workspace ออก เพราะไม่ได้ใช้ <<<
def wait_for_analysis(ce_task_url: str | None, s: Settings, timeout: int = 300) -> None:
    if not ce_task_url:
        raise RuntimeError("ไม่พบ ceTaskUrl")
    url = ce_task_url.replace(s.scanner_host_url, s.sonar_host_url)

    logger.info(f"[wait_for_analysis] polling {url}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = requests.get(url, auth=_auth(s), timeout=30).json()["task"]
        status = task["status"]
        if status == "SUCCESS":
            logger.info("[wait_for_analysis] analysis SUCCESS")
            return
        if status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"Sonar analysis {status}: {task.get('errorMessage', '(no message)')}")
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


# >>> แก้ไข: เปลี่ยน dict.fromkeys เป็น Dictionary Comprehension <<<
def _graph_metrics(graph: dict[str, set[str]]) -> dict:
    fan_in = {k: 0 for k in graph}
    for deps in graph.values():
        for target in deps:
            fan_in[target] += 1
    instability = [len(graph[k]) / (len(graph[k]) + fan_in[k]) for k in graph if graph[k] or fan_in[k]]
    return {
        "dep_modules": len(graph),
        "dep_edges": sum(len(v) for v in graph.values()),
        "dep_cycles": _count_cycles(graph),
        "dep_orphans": sum(1 for k in graph if not graph[k] and not fan_in[k]),
        "dep_avg_instability": round(sum(instability) / len(instability), 3) if instability else None,
        "dep_max_fan_out": max((len(v) for v in graph.values()), default=0),
        "dep_max_fan_in": max(fan_in.values(), default=0),
    }


def fetch_quality_gate(key: str, s: Settings) -> str:
    r = requests.get(
        f"{s.sonar_host_url}/api/qualitygates/project_status",
        params={"projectKey": key},
        auth=_auth(s),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["projectStatus"]["status"]