from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FC_", extra="ignore")

    sqlite_path: Path = Path("data/app.sqlite3")


settings = Settings()

