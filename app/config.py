from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    default_model: str = "gpt-4.1-mini"
    summary_model: str = ""
    translation_model: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def effective_summary_model(self) -> str:
        return self.summary_model or self.default_model

    @property
    def effective_translation_model(self) -> str:
        return self.translation_model or self.default_model


settings = Settings()
TEMP_DIR.mkdir(parents=True, exist_ok=True)
