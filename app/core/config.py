"""
Application settings — load từ env vars qua pydantic-settings.

Pattern: 1 class Settings duy nhất, inject qua FastAPI dependency.
Lý do dùng pydantic-settings:
- Type-safe (báo lỗi nếu env thiếu hoặc sai type)
- Validate ngay lúc startup (fail-fast)
- IDE autocomplete
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== App =====
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ===== Database =====
    database_url: PostgresDsn
    database_url_sync: PostgresDsn

    # ===== Redis =====
    redis_url: RedisDsn

    # ===== JWT =====
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ===== Business config =====
    timezone: str = "Asia/Ho_Chi_Minh"
    business_hour_start: int = Field(6, ge=0, le=23)
    business_hour_end: int = Field(22, ge=1, le=24)
    hold_duration_minutes: int = Field(10, gt=0)
    max_pending_bookings_per_user: int = Field(5, gt=0)
    slot_pregen_days: int = Field(30, gt=0)

    # ===== VNPay =====
    vnpay_tmn_code: str = ""
    vnpay_hash_secret: str = ""
    vnpay_payment_url: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    vnpay_return_url: str = "http://localhost:8000/payments/vnpay-return"

    # ===== Email =====
    smtp_host: str = ""
    smtp_port: int = 2525
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@booking.local"
    smtp_from_name: str = "Booking System"

    # ===== Owner seed =====
    seed_owner_email: str = "owner@booking.local"
    seed_owner_password: str = "changeme123"
    seed_tenant_name: str = "Default Tenant"

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Cache settings instance — load env file 1 lần duy nhất.
    Dùng qua FastAPI Depends(get_settings) hoặc gọi trực tiếp.
    """
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
