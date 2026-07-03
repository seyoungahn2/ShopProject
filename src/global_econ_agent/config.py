from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    newsapi_key: str = ""

    data_dir: Path = Path("./data")
    reports_dir: Path = Path("./reports")
    config_dir: Path = Path("./config")

    schedule_hour: int = 7
    schedule_minute: int = 0
    timezone: str = "Asia/Seoul"

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "agent.db"

    @property
    def settings_yaml(self) -> Path:
        return self.config_dir / "settings.yaml"

    @property
    def news_sources_yaml(self) -> Path:
        return self.config_dir / "news_sources.yaml"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings
