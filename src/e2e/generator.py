"""ขั้นตอนที่ 1: ให้ AI สร้างโปรเจกต์จาก prompt + environment"""
from __future__ import annotations

import time
from typing import Protocol

from .config import Settings
from .models import GeneratedFile, GenerationResult, Task

WRITE_PROJECT_TOOL = {
    "name": "write_project",
    "description": "Return every file of the generated project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "relative path, e.g. app/main.py"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            }
        },
        "required": ["files"],
    },
}


def build_prompts(task: Task) -> tuple[str, str]:
    env = task.environment
    constraints = "\n".join(f"- {c}" for c in env.get("constraints", []))
    system = (
        "You are a senior software engineer. Produce a complete, runnable project.\n"
        f"Language: {env.get('language')} {env.get('version', '')}\n"
        f"Frameworks/libraries: {', '.join(env.get('frameworks', []))}\n"
        f"Constraints:\n{constraints}\n"
        "Return the whole project ONLY by calling the write_project tool."
    )
    return system, task.prompt


class Generator(Protocol):
    def generate(self, task: Task) -> GenerationResult: ...


class AnthropicGenerator:
    def __init__(self, settings: Settings, model: str):
        import anthropic

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model

    def generate(self, task: Task) -> GenerationResult:
        system, user = build_prompts(task)
        t0 = time.time()
        with self.client.messages.stream(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[WRITE_PROJECT_TOOL],
            tool_choice={"type": "tool", "name": "write_project"},
        ) as stream:
            msg = stream.get_final_message()
        files: list[GeneratedFile] = []
        for block in msg.content:
            if block.type == "tool_use" and block.name == "write_project":
                files = [GeneratedFile(f["path"], f["content"]) for f in block.input.get("files", [])]
        if not files:
            raise RuntimeError("model returned no files")
        return GenerationResult(
            files=files,
            model=self.model,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            seconds=time.time() - t0,
        )


class MockGenerator:
    """ไม่เรียก AI — สร้างโปรเจกต์ตัวอย่าง (มี code smell ตั้งใจ) ไว้ทดสอบ pipeline"""

    def generate(self, task: Task) -> GenerationResult:
        main = '''import os


def divide(a, b):
    unused = 42
    try:
        return a / b
    except:
        return None


def password_check(p):
    password = "hunter2"
    return p == password
'''
        test = "from app.main import divide\n\n\ndef test_divide():\n    assert divide(4, 2) == 2\n"
        return GenerationResult(
            files=[
                GeneratedFile("app/__init__.py", ""),
                GeneratedFile("app/main.py", main),
                GeneratedFile("tests/test_main.py", test),
                GeneratedFile("requirements.txt", "pytest\n"),
            ],
            model="mock",
        )


def get_generator(provider: str, settings: Settings, model: str) -> Generator:
    if provider == "mock":
        return MockGenerator()
    if provider == "anthropic":
        return AnthropicGenerator(settings, model)
    raise ValueError(f"unknown provider: {provider}")
