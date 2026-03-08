"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./baires_talent_copilot.db"
    log_level: str = "INFO"
    auth_session_ttl_hours: int = 168
    bootstrap_demo_user: bool = True
    demo_user_email: str = "recruiter@baires.demo"
    demo_user_password: str = "TalentDemo2026!"
    demo_user_display_name: str = "Demo Recruiter"

    model_config = SettingsConfigDict(
        env_prefix="COPILOT_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
