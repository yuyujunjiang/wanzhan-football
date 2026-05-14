from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FC_", env_file=".env", extra="ignore")

    sqlite_path: Path = Path("data/app.sqlite3")
    ocr_provider: str = "stub"  # stub | paddle
    results_provider: str = "mock"  # mock | sporttery | football_data_org
    football_data_org_token: str | None = None

    # Matches cache (file-based). Intended to speed up /api/matches for schedule-heavy pages.
    matches_cache_dir: Path = Path("data/matches")
    matches_scheduler_enabled: bool = False
    matches_scheduler_interval_seconds: int = 300
    matches_scheduler_full_refresh_seconds: int = 1800


settings = Settings()
