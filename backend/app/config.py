"""
Application configuration.

All runtime configuration is loaded from environment variables (via a .env
file in local/dev, or real env vars in Docker/production). Nothing here is
hardcoded so the same image can be reused across environments.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 800

    # --- LangSmith (optional; falls back gracefully if unset) ---
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "Amex-catchup-demo"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # --- App / server ---
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    app_env: str = "local"

    # --- Demo behavior ---
    simulate_llm_latency_ms: int = 0  # optional artificial delay for demo pacing

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def langsmith_enabled(self) -> bool:
        return bool(self.langchain_tracing_v2 and self.langchain_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
