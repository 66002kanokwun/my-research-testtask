import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    ai_provider: str = os.getenv("AI_PROVIDER", "anthropic")
    ai_model: str = os.getenv("AI_MODEL", "claude-sonnet-5-5")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    sonar_host_url: str = os.getenv("SONAR_HOST_URL", "http://localhost:9000").rstrip("/")
    sonar_token: str = os.getenv("SONAR_TOKEN", "")
    scanner_mode: str = os.getenv("SONAR_SCANNER_MODE", "local")
    scanner_bin: str = os.getenv("SONAR_SCANNER_BIN", "sonar-scanner")
    scanner_host_url: str = os.getenv("SONAR_SCANNER_HOST_URL", "http://host.docker.internal:9000")
    workspaces_dir: Path = ROOT / os.getenv("WORKSPACES_DIR", "workspaces")
    db_path: Path = ROOT / os.getenv("DB_PATH", "results.db")


def get_settings() -> Settings:
    return Settings()
