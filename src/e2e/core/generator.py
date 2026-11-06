"""ขั้นตอนที่ 1: ให้ AI สร้างโปรเจกต์จาก prompt + environment"""
from __future__ import annotations

import json
import time
from typing import Protocol

from ..config import Settings
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
    # >>> เพิ่มการ print ข้อความดิบที่ AI ตอบมาเพื่อ Debug <<<
    stripped = _strip_code_fence(text)
    if not stripped:
        raise RuntimeError("Model returned empty content")
    
    # ลอง parse JSON
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        # ถ้า parse ไม่ได้ ให้โชว์ข้อความที่ AI ตอบมา (200 ตัวอักษรแรก)
        snippet = stripped[:200].replace("\n", " ")
        raise RuntimeError(
            f"Failed to parse JSON from model output. "
            f"Error: {e}. "
            f"Model said: '{snippet}...'"
        )
    
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
        if not choice.message.content:
            raise RuntimeError("Model returned empty content (finish_reason=stop)")
        return GenerationResult(
            files=parse_files(choice.message.content),
            model=self.model,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            seconds=time.time() - t0,
        )


class MockGenerator:
    """ไม่เรียก AI — สร้างโปรเจกต์ React ตัวอย่าง (จงใจใส่ Bug และ Code Smell) ไว้ทดสอบ pipeline"""

    def generate(self, task: Task) -> GenerationResult:
        # จงใจใส่:
        # 1. Bug: ใช้ == แทน ===
        # 2. Vulnerability: Hardcoded AWS Key
        # 3. Code Smell: ฟังก์ชันซับซ้อน (processData)
        # 4. Code Smell: ตัวแปรไม่ถูกใช้งาน (unusedVariable)
        app = '''import { useState, useMemo } from "react";

export default function App() {
  const [todos, setTodos] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState("");

  // [Vulnerability] Hardcoded Secret
  const AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE";

  // [Code Smell] Unused variable
  const unusedVariable = "hello world";

  // [Code Smell] High Cognitive Complexity
  const processData = (data) => {
    let res = 0;
    if (data) {
      for (let i = 0; i < data.length; i++) {
        if (data[i] > 0) {
          if (data[i] % 2 === 0) { res += 2; } else { res += 1; }
        } else {
          if (data[i] < -10) { res -= 5; } else { res -= 1; }
        }
      }
    }
    return res;
  };

  const remaining = useMemo(
    () => todos.filter((t) => !t.done).length,
    [todos]
  );

  const visible = useMemo(() => {
    if (filter === "active") return todos.filter((t) => !t.done);
    if (filter === "done") return todos.filter((t) => t.done);
    return todos;
  }, [todos, filter]);

  const add = () => {
    if (!text.trim()) {
      setError("Please enter a title");
      return;
    }
    setTodos([...todos, { id: Date.now(), title: text.trim(), done: false }]);
    setText("");
    setError("");
  };

  const toggle = (id) => {
    // [Bug] ใช้ == แทน === (SonarQube จะจับข้อนี้)
    if (id == 0) { console.log("zero"); } 
    setTodos(todos.map((t) => t.id === id ? { ...t, done: !t.done } : t));
  };
  
  const remove = (id) => setTodos(todos.filter((t) => t.id !== id));
  const startEdit = (t) => { setEditingId(t.id); setEditText(t.title); };
  const saveEdit = () => {
    setTodos(todos.map((t) => t.id === editingId ? { ...t, title: editText } : t));
    setEditingId(null);
  };

  return (
    <div>
      <input data-testid="todo-input" value={text} onChange={(e) => setText(e.target.value)} />
      <button data-testid="add-button" onClick={add}>Add</button>
      {error && <p data-testid="error-message">{error}</p>}
      <ul>
        {visible.map((t) => (
          <li key={t.id} data-testid="todo-item">
            {editingId === t.id ? (
              <>
                <input data-testid="todo-edit-input" value={editText} onChange={(e) => setEditText(e.target.value)} />
                <button data-testid="todo-save" onClick={saveEdit}>Save</button>
              </>
            ) : (
              <>
                <span data-testid="todo-title">{t.title}</span>
                <input data-testid="todo-toggle" type="checkbox" checked={t.done} onChange={() => toggle(t.id)} />
                <button data-testid="todo-edit" onClick={() => startEdit(t)}>Edit</button>
                <button data-testid="todo-delete" onClick={() => remove(t.id)}>Delete</button>
              </>
            )}
          </li>
        ))}
      </ul>
      <div>
        <button data-testid="filter-all" onClick={() => setFilter("all")}>All</button>
        <button data-testid="filter-active" onClick={() => setFilter("active")}>Active</button>
        <button data-testid="filter-done" onClick={() => setFilter("done")}>Done</button>
      </div>
      <p data-testid="remaining-count">{remaining} remaining</p>
    </div>
  );
}
'''
        test = '''import { test, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App.jsx";

test("renders the form", () => {
  render(<App />);
  expect(screen.getByTestId("todo-input")).toBeTruthy();
});
'''
        pkg = json.dumps({
            "name": f"mock-{task.id}",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "test": "vitest run",
            },
            "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
            "devDependencies": {
                "vite": "^5.4.0",
                "@vitejs/plugin-react": "^4.3.0",
                "vitest": "^2.0.0",
                "@vitest/coverage-v8": "^2.0.0",
                "jsdom": "^25.0.0",
                "@testing-library/react": "^16.0.0",
                "@testing-library/user-event": "^14.5.0",
            },
        }, indent=2)

        vite_config = '''import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    coverage: { provider: "v8", reporter: ["lcov", "text"] },
  },
});
'''
        index_html = '''<!doctype html>
<html>
  <head><meta charset="utf-8" /><title>Mock Todo</title></head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''
        main_jsx = '''import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
'''

        return GenerationResult(
            files=[
                GeneratedFile("package.json", pkg),
                GeneratedFile("vite.config.js", vite_config),
                GeneratedFile("index.html", index_html),
                GeneratedFile("src/main.jsx", main_jsx),
                GeneratedFile("src/App.jsx", app),
                GeneratedFile("src/App.test.jsx", test),
            ],
            model="mock",
        )


def get_generator(provider: str, settings: Settings, model: str) -> Generator:
    if provider == "mock":
        return MockGenerator()
    if provider == "deepseek":
        return DeepSeekGenerator(settings, model)
    raise ValueError(f"unknown provider: {provider}")