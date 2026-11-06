"""ร้อย flow ทั้งหมดเข้าด้วยกัน: generate -> write -> checks -> sonar -> store"""
from __future__ import annotations

import traceback

from ..integrations import sandbox, sonar, storage
from ..config import get_settings
from .generator import get_generator
from .models import Task
from ..utils.logger import logger


def run_pipeline(task_path: str, provider: str | None = None, model: str | None = None, run_id: int | None = None) -> int:
    s = get_settings()
    task = Task.load(task_path)
    provider = provider or s.ai_provider
    model = model or s.ai_model
    if run_id is None:
        run_id = storage.create_run(task.id, task.name, provider, model)

    try:
        storage.update_run(run_id, step="generating")
        logger.info(f"Run #{run_id}: Generating code with {provider}/{model}")
        gen = get_generator(provider, s, model).generate(task)
        storage.update_run(
            run_id, gen_seconds=gen.seconds, input_tokens=gen.input_tokens, output_tokens=gen.output_tokens, model=gen.model
        )

        storage.update_run(run_id, step="writing workspace")
        ws = sandbox.write_workspace(s.workspaces_dir / f"{task.id}-{run_id}", gen.files)

        sandbox.inject_acceptance_tests(ws, task.acceptance_tests)
        if task.checks and task.environment.get("docker_image"):
            storage.update_run(run_id, step="running checks")
            results = sandbox.run_checks_in_docker(ws, task.environment["docker_image"], task.checks)
            gate_names = {c["name"] for c in task.checks if not c.get("always")}
            storage.update_run(
                run_id,
                checks=results,
                tests_passed=int(all(r["status"] == "pass" for r in results if r["name"] in gate_names)),
            )

        storage.update_run(run_id, step="sonar scan")
        key = sonar.project_key(task.id, gen.model)
        ce_task_url = sonar.run_scanner(ws, key, s, task.sonar.get("properties", {}), version=str(run_id))
        
        # >>> แก้ไขตรงนี้: ลบ ws ออกจากการเรียก wait_for_analysis <<<
        sonar.wait_for_analysis(ce_task_url, s) 

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
        logger.info(f"Run #{run_id} finished successfully. Quality Gate: {gate}")
    except Exception as e:
        logger.error(f"Run #{run_id} failed: {e}")
        storage.update_run(
            run_id, status="failed", error=f"{e}\n{traceback.format_exc()[-1500:]}", finished_at=storage.now()
        )
    return run_id