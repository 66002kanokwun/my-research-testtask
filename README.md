# E2E AI Code Quality Evaluator

Task spec (YAML) → AI สร้างโปรเจกต์ → (รันเทสต์ใน Docker) → SonarQube scan → เก็บ metrics (SQLite) → Dashboard

```
tasks/*.yaml ──► generator ──► workspaces/<task>-<run>/ ──► sonar-scanner ──► SonarQube
                                                                                │ REST API
                     dashboard (FastAPI + Chart.js) ◄── results.db ◄────────────┘
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # ใส่ ANTHROPIC_API_KEY และ SONAR_TOKEN

docker compose up -d                                   # SonarQube ที่ http://localhost:9000 (admin/admin)
# My Account > Security > Generate token -> ใส่ใน .env (SONAR_TOKEN)
# ติดตั้ง sonar-scanner CLI หรือตั้ง SONAR_SCANNER_MODE=docker
```

## Run
```bash
export PYTHONPATH=src                                  # Windows: $env:PYTHONPATH="src"
python -m e2e.cli run tasks/todo-api.yaml --provider mock   # ทดสอบ pipeline โดยไม่เรียก AI
python -m e2e.cli run tasks/todo-api.yaml                   # ใช้ AI จริง
python -m e2e.cli serve                                      # dashboard http://localhost:8000
pytest
```

## เพิ่ม task ใหม่
copy `tasks/todo-api.yaml` แล้วแก้ `prompt`, `environment`, `metrics`

## Roadmap
- เปรียบเทียบหลาย model พร้อมกัน (loop provider/model ใน pipeline)
- รัน N ครั้งต่อ task แล้วหา mean/variance (AI output ไม่ deterministic)
- เพิ่ม provider อื่นใน `generator.py` (OpenAI, Gemini, local)
- ย้าย SQLite → Postgres, เพิ่ม queue (Celery/RQ) ถ้ารันหลาย job
- เพิ่ม metric นอก Sonar: test pass rate, token cost, latency
