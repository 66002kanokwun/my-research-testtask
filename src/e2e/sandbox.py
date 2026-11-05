"""เขียนไฟล์ลง workspace, รันด่านตรวจใน Docker และอ่านผลมาเป็น metrics"""
from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
from pathlib import Path

from .models import GeneratedFile

RESULTS_DIR = ".results"
CODE_EXT = (".js", ".jsx", ".mjs", ".cjs")


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


def inject_acceptance_tests(workspace: Path, tests: dict[str, str]) -> None:
    """ใส่เทสต์ของเรา (AI ไม่เคยเห็น) หลัง AI สร้างโปรเจกต์เสร็จแล้ว"""
    for rel, content in tests.items():
        target = safe_join(workspace, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def run_checks_in_docker(workspace: Path, image: str, checks: list[dict]) -> list[dict]:
    """รันด่านตามลำดับ ถ้าด่านที่ required พัง ด่านที่เหลือจะถูกข้าม (ยกเว้นด่านที่มี always)
    โค้ดจาก AI ไม่ควรรันบนเครื่องตรงๆ จึงรันใน container"""
    results: list[dict] = []
    blocked = False
    for chk in checks:
        if blocked and not chk.get("always"):
            results.append({"name": chk["name"], "status": "skipped", "output": ""})
            continue
        cmd = ["docker", "run", "--rm", "-v", f"{workspace.resolve()}:/work", "-w", "/work",
               image, "sh", "-c", chk["command"]]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=int(chk.get("timeout", 600)))
            ok, out = p.returncode == 0, (p.stdout + p.stderr)[-2000:]
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            ok, out = False, f"{type(e).__name__}: {e}"
        results.append({"name": chk["name"], "status": "pass" if ok else "fail", "output": out})
        if not ok and chk.get("required"):
            blocked = True
    return results


class _CycleCounter:
    """Tarjan SCC: นับกลุ่มไฟล์ที่ import วนกัน (รวมกรณี import ตัวเอง)"""

    def __init__(self, graph: dict[str, set[str]]):
        self.graph = graph
        self.index: dict[str, int] = {}
        self.low: dict[str, int] = {}
        self.stack: list[str] = []
        self.on_stack: set[str] = set()
        self.cycles = 0

    def count(self) -> int:
        for v in self.graph:
            if v not in self.index:
                self._visit(v)
        return self.cycles

    def _visit(self, v: str) -> None:
        self.index[v] = self.low[v] = len(self.index)
        self.stack.append(v)
        self.on_stack.add(v)
        for w in self.graph.get(v, ()):
            self._visit_neighbor(v, w)
        if self.low[v] == self.index[v]:
            self._close_component(v)

    def _visit_neighbor(self, v: str, w: str) -> None:
        if w not in self.index:
            self._visit(w)
            self.low[v] = min(self.low[v], self.low[w])
        elif w in self.on_stack:
            self.low[v] = min(self.low[v], self.index[w])

    def _close_component(self, root: str) -> None:
        size = 0
        while True:
            w = self.stack.pop()
            self.on_stack.discard(w)
            size += 1
            if w == root:
                break
        if size > 1 or root in self.graph.get(root, ()):
            self.cycles += 1


def _count_cycles(graph: dict[str, set[str]]) -> int:
    return _CycleCounter(graph).count()


def _read_result(workspace: Path, name: str):
    return json.loads((workspace / RESULTS_DIR / name).read_text(encoding="utf-8"))


def collect_functional_metrics(workspace: Path) -> dict:
    """Functional Suitability: สัดส่วน acceptance test ที่ผ่าน"""
    try:
        data = _read_result(workspace, "acceptance.json")
        total, passed = int(data["numTotalTests"]), int(data["numPassedTests"])
    except (OSError, ValueError, KeyError):
        # เทสต์รันไม่ได้เลย (install/build พัง ฯลฯ) นับเป็น 0
        return {"func_passed": 0, "func_total": None, "func_pass_rate": 0.0}
    return {
        "func_passed": passed,
        "func_total": total,
        "func_pass_rate": round(passed / total, 3) if total else 0.0,
    }


def _build_import_graph(raw: dict) -> dict[str, set[str]]:
    """แปลงผลของ Dependency Cruiser เป็นกราฟ: ไฟล์ -> ไฟล์ที่มัน import (เฉพาะโค้ดในโปรเจกต์)"""
    modules = [m for m in raw["modules"] if m["source"].endswith(CODE_EXT)]
    graph: dict[str, set[str]] = {m["source"]: set() for m in modules}
    for m in modules:
        for d in m.get("dependencies", []):
            target = d.get("resolved")
            if "local" in d.get("dependencyTypes", []) and target in graph:
                graph[m["source"]].add(target)
    return graph


def _graph_metrics(graph: dict[str, set[str]]) -> dict:
    fan_in = dict.fromkeys(graph, 0)
    for deps in graph.values():
        for target in deps:
            fan_in[target] += 1
    # instability = Ce / (Ca + Ce): 0 = เสถียร, 1 = พึ่งพาคนอื่นมาก
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


def collect_design_metrics(workspace: Path) -> dict:
    """Design Maintainability: อ่านผลของ Dependency Cruiser และ Madge
    ถ้าไม่มีไฟล์ผล จะไม่ใส่ metric นั้น (dashboard แสดง "-")"""
    out: dict = {}
    with contextlib.suppress(OSError, ValueError, KeyError):
        out.update(_graph_metrics(_build_import_graph(_read_result(workspace, "depcruise.json"))))
    with contextlib.suppress(OSError, ValueError):
        out["dep_cycles_madge"] = len(_read_result(workspace, "madge.json"))
    return out