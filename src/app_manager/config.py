"""Configuration management using pydantic-settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_comma_separated_ints(v) -> list[int]:
    """Parse comma-separated integers from string or return list as-is."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        if not v.strip():
            return []
        return [int(uid.strip()) for uid in v.split(",") if uid.strip()]
    return []


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot
    telegram_bot_token: str = Field(description="Telegram Bot API token")

    # Security - User IDs (stored as comma-separated strings in env)
    admin_user_ids: str = Field(
        default="",
        description="Telegram user IDs with admin privileges (comma-separated)",
    )
    allowed_user_ids: str = Field(
        default="",
        description="Telegram user IDs allowed to use the bot (comma-separated)",
    )

    # Apps Configuration
    apps_config_path: str = Field(
        default="apps.yaml",
        description="Path to apps configuration file",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def admin_ids(self) -> list[int]:
        """Get admin user IDs as list."""
        return parse_comma_separated_ints(self.admin_user_ids)

    @property
    def allowed_ids(self) -> list[int]:
        """Get allowed user IDs as list."""
        return parse_comma_separated_ints(self.allowed_user_ids)

    @property
    def all_authorized_users(self) -> set[int]:
        """Get all authorized user IDs (admins + allowed users)."""
        return set(self.admin_ids) | set(self.allowed_ids)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin."""
        return user_id in self.admin_ids

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized (admin or allowed)."""
        return user_id in self.all_authorized_users


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
