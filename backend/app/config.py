from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    database_url: str = "postgresql+psycopg://hirepilot:change_me@localhost:5432/hirepilot"
    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 10
    cors_origins: str = "http://localhost:8501,http://localhost:3000"
    app_env: str = "development"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
