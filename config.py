"""
Configuration management with validation
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """Application settings with validation"""

    # App settings
    app_name: str = "Email Service API"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # SMTP settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = "tech@asklena.ai"
    sender_name: str = "Lena (AskLena.AI)"
    email_password: str

    # Email settings
    email_template_path: str = "email_template.html"
    email_timeout: int = 30
    email_max_retries: int = 3
    email_retry_delay: int = 2

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 10
    rate_limit_window: int = 60  # seconds

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Security
    allowed_ip_addresses: list[str] = []  # Empty means all IPs allowed

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
