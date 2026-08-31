from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

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
    # DeepSeek V4 Flash serveras via OpenRouter (env-var-namn behålls för kompatibilitet)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek/deepseek-v4-pro-0813"
    FINNHUB_API_KEY: str = ""

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://marketscan.vercel.app", "https://web-hankkontakts-projects.vercel.app"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
