from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("/app/data")
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    llm_base_url: str = ""          # optional custom base URL for any provider
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    tz: str = "Asia/Tehran"
    match_confidence_auto: int = 90
    match_confidence_confirm: int = 70

    @property
    def active_dir(self) -> Path:
        return self.data_dir / "active"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def workbook_path(self) -> Path:
        return self.active_dir / "diet_plan.xlsx"

    @property
    def db_path(self) -> Path:
        return self.active_dir / "app.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
