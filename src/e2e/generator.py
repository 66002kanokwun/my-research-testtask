"""ขั้นตอนที่ 1: ให้ AI สร้างโปรเจกต์จาก prompt + environment"""
from __future__ import annotations

import json
import time
from typing import Protocol

from .config import Settings
from .models import GeneratedFile, GenerationResult, Task


def build_prompts(task: Task) -> tuple[str, str]:
    env = task.environment
    constraints = "\n".join(f"- {c}" for c in env.get("constraints", []))
    system = (
        "You are a senior front-end engineer. Produce a complete, runnable project.\n"
        f"Language: {env.get('language')} {env.get('version', '')} (JavaScript/JSX only, never TypeScript)\n"
        f"Frameworks/libraries: {', '.join(env.get('frameworks', []))}\n"
        f"Constraints:\n{constraints}\n"
        "Include every file needed to run: package.json, config files, source code and tests.\n"
        "Respond with a single JSON object and nothing else, in exactly this format:\n"
        '{"files": [{"path": "src/App.jsx", "content": "file content here"}]}'
    )
    return system, task.prompt


def _strip_code_fence(text: str) -> str:
    """ตัด ```json ... ``` ที่โมเดลอาจห่อมา (ไม่ใช้ regex เพื่อเลี่ยง backtracking)"""
    text = text.strip()
    if not text.startswith("```"):
        return text
    first_line, newline, rest = text.partition("\n")
    body = rest if newline else first_line.removeprefix("```json").removeprefix("```")
    return body.removesuffix("```").strip()


def parse_files(text: str) -> list[GeneratedFile]:
    data = json.loads(_strip_code_fence(text))
    files = [GeneratedFile(f["path"], f["content"]) for f in data.get("files", [])]
    if not files:
        raise RuntimeError("model returned no files")
    return files


class Generator(Protocol):
    def generate(self, task: Task) -> GenerationResult: ...


class DeepSeekGenerator:
    def __init__(self, settings: Settings, model: str):
        from openai import OpenAI

        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=900,
        )
        self.model = model
        self.max_tokens = settings.ai_max_tokens

    def generate(self, task: Task) -> GenerationResult:
        system, user = build_prompts(task)
        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            max_tokens=self.max_tokens,
        )
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            raise RuntimeError("output truncated: increase AI_MAX_TOKENS or simplify the task")
        return GenerationResult(
            files=parse_files(choice.message.content),
            model=self.model,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            seconds=time.time() - t0,
        )


class MockGenerator:
    """ไม่เรียก AI — สร้างโปรเจกต์ React ตัวอย่าง (มี code smell ตั้งใจ) ไว้ทดสอบ pipeline"""

    def generate(self, task: Task) -> GenerationResult:
        app = '''import { useState } from "react";

export default function App() {
  const [todos, setTodos] = useState([]);
  const unused = 42;
  const password = "hunter2";
  return <ul>{todos.map((t, i) => <li key={i}>{t}</li>)}</ul>;
}
'''
        test = 'import { test, expect } from "vitest";\n\ntest("sanity", () => expect(1).toBe(1));\n'
        pkg = json.dumps({
            "name": f"mock-{task.id}", "private": True, "type": "module",
            "scripts": {"test": "vitest run"},
            "dependencies": {"react": "^18.3.1"},
            "devDependencies": {"vitest": "^2.0.0", "@vitest/coverage-v8": "^2.0.0"},
        }, indent=2)
        return GenerationResult(
            files=[
                GeneratedFile("package.json", pkg),
                GeneratedFile("src/App.jsx", app),
                GeneratedFile("src/App.test.js", test),
            ],
            model="mock",
        )


def get_generator(provider: str, settings: Settings, model: str) -> Generator:
    if provider == "mock":
        return MockGenerator()
    if provider == "deepseek":
        return DeepSeekGenerator(settings, model)
    raise ValueError(f"unknown provider: {provider}")