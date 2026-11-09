import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "paypilot"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    default_currency: str = "INR"
    default_tax_rate: float = 18.0

    # PayPal Configuration
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_mode: str = "sandbox"  # 'sandbox' or 'live'
    paypal_webhook_id: str = ""

    # AI Intelligence Configuration (Phase 4)
    ai_provider: str = "gemini"  # 'gemini' or 'openai'
    ai_model: str = "gemini-1.5-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ai_temperature: float = 0.2
    ai_max_tokens: int = 1500

    # Phase 6: Automation, Notification & Financial Intelligence
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    notification_email_from: str = "notifications@paypilot.in"
    email_delivery_enabled: bool = False
    upcoming_due_window_days: int = 3
    reminder_dedup_window_days: int = 3
    anomaly_large_tx_multiplier: float = 2.5

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def paypal_api_base(self) -> str:
        if self.paypal_base_url:
            return self.paypal_base_url.rstrip("/")
        return "https://api-m.paypal.com" if self.paypal_mode == "live" else "https://api-m.sandbox.paypal.com"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH if os.path.exists(ENV_PATH) else ".env",
        case_sensitive=False,
        extra="allow",
    )

settings = Settings()
