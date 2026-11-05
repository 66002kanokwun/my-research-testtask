"""ร้อย flow ทั้งหมดเข้าด้วยกัน: generate -> write -> checks -> sonar -> store"""
from __future__ import annotations

import traceback

from . import sandbox, sonar, storage
from .config import get_settings
from .generator import get_generator
from .models import Task


def run_pipeline(task_path: str, provider: str | None = None, model: str | None = None, run_id: int | None = None) -> int:
    s = get_settings()
    task = Task.load(task_path)
    provider = provider or s.ai_provider
    model = model or s.ai_model
    if run_id is None:
        run_id = storage.create_run(task.id, task.name, provider, model)

    try:
        storage.update_run(run_id, step="generating")
        gen = get_generator(provider, s, model).generate(task)
        storage.update_run(
            run_id, gen_seconds=gen.seconds, input_tokens=gen.input_tokens, output_tokens=gen.output_tokens, model=gen.model
        )

        storage.update_run(run_id, step="writing workspace")
        ws = sandbox.write_workspace(s.workspaces_dir / f"{task.id}-{run_id}", gen.files)

        # ใส่เทสต์ของเราหลังเขียน workspace เสมอ เพื่อไม่ให้ AI เขียนทับ/เห็นล่วงหน้า
        sandbox.inject_acceptance_tests(ws, task.acceptance_tests)
        if task.checks and task.environment.get("docker_image"):
            storage.update_run(run_id, step="running checks")
            results = sandbox.run_checks_in_docker(ws, task.environment["docker_image"], task.checks)
            # ด่านที่มี always เป็นการวิเคราะห์ ไม่นับเป็นเงื่อนไขผ่าน/ไม่ผ่านของโปรเจกต์
            gate_names = {c["name"] for c in task.checks if not c.get("always")}
            storage.update_run(
                run_id,
                checks=results,
                tests_passed=int(all(r["status"] == "pass" for r in results if r["name"] in gate_names)),
            )

        storage.update_run(run_id, step="sonar scan")
        key = sonar.project_key(task.id, gen.model)
        sonar.run_scanner(ws, key, s, task.sonar.get("properties", {}), version=str(run_id))
        sonar.wait_for_analysis(ws, s)

        storage.update_run(run_id, step="collecting metrics")
        metrics = sonar.fetch_measures(key, task.metrics, s)
        if task.checks:
            metrics.update(sandbox.collect_functional_metrics(ws))
            metrics.update(sandbox.collect_design_metrics(ws))
        gate = sonar.fetch_quality_gate(key, s)
        storage.update_run(
            run_id,
            metrics=metrics,
            quality_gate=gate,
            sonar_url=f"{s.sonar_host_url}/dashboard?id={key}",
            status="done",
            step="finished",
            finished_at=storage.now(),
        )
    except Exception as e:  # noqa: BLE001
        storage.update_run(
            run_id, status="failed", error=f"{e}\n{traceback.format_exc()[-1500:]}", finished_at=storage.now()
        )
    return run_id