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

    @classmethod
    def load(cls, path: str | Path) -> "Task":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        for key in ("id", "name", "prompt", "environment"):
            if key not in data:
                raise ValueError(f"task file missing required field: {key}")
        return cls(
            id=data["id"],
            name=data["name"],
            prompt=data["prompt"],
            environment=data["environment"],
            sonar=data.get("sonar", {}) or {},
            metrics=data.get("metrics", []) or [],
        )


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
