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

    # Comma-separated browser origins for CORS (required when frontend calls API on another port/host).
    # Example: https://yujj.club,http://localhost:3000
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://0.0.0.0:3000"
    )
    # Set FC_COOKIE_SECURE=1 behind HTTPS reverse proxy so session cookies are Secure.
    cookie_secure: bool = False

    fastgpt_api_base: str = "http://175.27.228.129:4000/api"
    fastgpt_api_key: str | None = None
    fastgpt_chat_path: str = "/v1/chat/completions"
    fastgpt_timeout_seconds: float = 30.0

    @property
    def fastgpt_chat_url(self) -> str:
        base = self.fastgpt_api_base.rstrip("/")
        path = (
            self.fastgpt_chat_path
            if self.fastgpt_chat_path.startswith("/")
            else f"/{self.fastgpt_chat_path}"
        )
        return f"{base}{path}"


settings = Settings()
