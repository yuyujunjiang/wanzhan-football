from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FC_", extra="ignore")

    sqlite_path: Path = Path("data/app.sqlite3")
    ocr_provider: str = "stub"  # stub | paddle
    results_provider: str = "mock"  # mock | football_data_org
    football_data_org_token: str | None = None


settings = Settings()

