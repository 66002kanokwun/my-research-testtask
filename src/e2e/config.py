import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# หา Root Directory ของโปรเจกต์
ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # AI Provider
    ai_provider: str = "deepseek"
    ai_model: str = "deepseek-chat"
    ai_max_tokens: int = 8000
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # SonarQube
    sonar_host_url: str = "http://localhost:9000"
    sonar_token: str = ""
    scanner_mode: str = "docker"
    scanner_bin: str = "sonar-scanner"
    scanner_host_url: str = "http://host.docker.internal:9000"

    # Paths
    workspaces_dir: Path = ROOT / "workspaces"
    db_path: Path = ROOT / "results.db"

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

# Singleton instance
_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings