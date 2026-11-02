from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="IGD_")

    api_key: str = "change-me"
    download_dir: Path = Path("./downloads")
    db_path: Path = Path("./jobs.db")
    max_workers: int = 2
    max_posts_per_profile: int = 12
    rate_limit: str = "10/minute"
    ig_username: str | None = None          # optional, improves reliability
    ig_session_file: Path | None = None     # created via `instaloader -l USER`


settings = Settings()
settings.download_dir.mkdir(parents=True, exist_ok=True)
