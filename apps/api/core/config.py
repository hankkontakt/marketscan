from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Cloudflare R2
    R2_KEY_ID: str = ""
    R2_SECRET: str = ""
    R2_ENDPOINT: str = ""
    R2_BUCKET: str = "marketscan-data"

    # External APIs
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    FINNHUB_API_KEY: str = ""

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://marketscan.vercel.app"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
