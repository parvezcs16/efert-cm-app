from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Central Mess Management System"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://mess:mess@localhost:5432/mess"

    cors_origins: str = "http://localhost:5173"

    secret_key: str = "change-me-in-production"

    allowed_email_domains: str = "example.com"

    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Uploaded files (menu images) are written under media_root and served
    # read-only at media_url_prefix.
    media_root: str = "media"
    media_url_prefix: str = "/media"
    max_image_upload_bytes: int = 5 * 1024 * 1024

    # "End of day" for the daily served-orders notification, in the mess's
    # local time. A fixed UTC offset (minutes) rather than a tz name keeps
    # this free of a tzdata dependency; the default is PKT (UTC+5, no DST).
    business_utc_offset_minutes: int = 300
    daily_summary_hour: int = 21

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_email_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
