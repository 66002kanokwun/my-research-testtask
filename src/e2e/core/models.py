from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class Task:
    id: str
    name: str
    prompt: str
    environment: dict[str, Any]
    sonar: dict[str, Any] = field(default_factory=dict)
    metrics: list[str] = field(default_factory=list)
    acceptance_tests: dict[str, str] = field(default_factory=dict)
    checks: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "Task":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")
            
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError(f"Task file is empty: {path}")
            
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Task file is empty or invalid YAML: {path}")

        cls._validate_required_fields(data, ("id", "name"))

        # 1. โหลด Base Config (แบบ Recursive)
        merged_data = cls._load_base_config(path, data)

        # 2. Override ด้วยค่าจาก Task หลัก
        cls._apply_overrides(merged_data, data)

        # 3. โหลด Prompt
        prompt = cls._load_prompt(path, data)

        # 4. โหลด Acceptance Tests
        acceptance_tests = cls._load_acceptance_tests(path, data, merged_data)

        # 5. ตรวจสอบ required fields ใน merged_data
        cls._validate_required_fields(merged_data, ("environment",), " (check base_config)")

        return cls(
            id=data["id"],
            name=data["name"],
            prompt=prompt,
            environment=merged_data.get("environment", {}),
            sonar=merged_data.get("sonar", {}) or {},
            metrics=merged_data.get("metrics", []) or [],
            acceptance_tests=acceptance_tests,
            checks=merged_data.get("checks", []) or [],
        )

    # ---------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------

    @staticmethod
    def _validate_required_fields(data: dict, fields: tuple[str, ...], hint: str = "") -> None:
        for key in fields:
            if key not in data:
                raise ValueError(f"task file missing required field: {key}{hint}")

    @classmethod
    def _load_base_config(cls, current_path: Path, current_data: dict) -> dict[str, Any]:
        """โหลด Base Config แบบ Recursive (รองรับการซ้อนกันหลายชั้น)"""
        merged_data: dict[str, Any] = {}
        
        if "base_config" not in current_data:
            return merged_data
            
        base_path = (current_path.parent / current_data["base_config"]).resolve()
        if not base_path.exists():
            raise FileNotFoundError(f"Base config not found: {base_path}")
            
        base_data = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        if base_data:
            # Recursive: ถ้า base ตัวนี้มี base_config ของตัวเองอีก ให้โหลดต่อ
            if "base_config" in base_data:
                nested_base = cls._load_base_config(base_path, base_data)
                merged_data.update(nested_base)
            
            # แล้วค่อยทับด้วยค่าของ base ตัวนี้
            merged_data.update(base_data)
            
        return merged_data

    @staticmethod
    def _apply_overrides(merged_data: dict[str, Any], data: dict) -> None:
        # รวม Checks (ถ้าทั้ง base และ task ต่างมี checks ให้เอามาต่อกัน)
        if "checks" in data and "checks" in merged_data:
            # เก็บ checks ของ base ไว้ก่อน แล้วเอา checks ของ task ต่อท้าย
            base_checks = merged_data["checks"]
            task_checks = data["checks"]
            merged_data["checks"] = base_checks + task_checks
            data = data.copy() # Copy เพื่อไม่ให้กระทบ dict เดิม
            del data["checks"] # ลบออกเพื่อไม่ให้โดน override ทับ

        # Override ค่าอื่นๆ ตามปกติ
        for k, v in data.items():
            if not k.endswith("_file") and k != "base_config":
                merged_data[k] = v

    @staticmethod
    def _load_prompt(path: Path, data: dict) -> str:
        prompt = data.get("prompt", "")
        if "prompt_file" in data:
            prompt_path = (path.parent / data["prompt_file"]).resolve()
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            prompt = prompt_path.read_text(encoding="utf-8")

        if not prompt:
            raise ValueError("Task must have either 'prompt' or 'prompt_file'")
        return prompt

    @staticmethod
    def _load_acceptance_tests(path: Path, data: dict, merged_data: dict) -> dict[str, str]:
        acceptance_tests = merged_data.get("acceptance_tests", {})
        if "acceptance_file" in data:
            acc_path = (path.parent / data["acceptance_file"]).resolve()
            if not acc_path.exists():
                raise FileNotFoundError(f"Acceptance file not found: {acc_path}")
            acceptance_tests = yaml.safe_load(acc_path.read_text(encoding="utf-8")) or {}
        return acceptance_tests


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class GenerationResult:
    files: list[GeneratedFile]
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0