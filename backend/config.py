from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # fallback LLM server — runs locally via `make fallback-server`
    fallback_server_url: str = "http://localhost:4000"
    fallback_model: str = "t0-deepseek"

    # kept for backward compat but unused — we call the fallback server instead
    openai_api_key: str = ""

    libretranslate_url: str = "http://localhost:5000"
    libretranslate_api_key: str = ""

    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    inbound_email: str = ""

    public_base_url: str = "http://localhost:5173"

    admin_email: str = "admin@ai020.local"
    admin_password_hash: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    database_url: str = "sqlite:///./ai020.db"
    storage_dir: str = "./storage"
    emails_dir: str = "../emails"
    default_from_email: str = "AI020 <noreply@ai020.local>"


settings = Settings()
