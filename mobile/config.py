"""BrowserStack configuration read only when a Mobile fixture requests it."""

from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


ROOT = Path(__file__).resolve().parents[1]


class MobileSettings(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, hide_input_in_errors=True)

    username: SecretStr = Field(alias="BROWSERSTACK_USERNAME")
    access_key: SecretStr = Field(alias="BROWSERSTACK_ACCESS_KEY")
    app_url: str = Field(alias="BROWSERSTACK_APP_URL", pattern=r"^bs://[A-Za-z0-9]+$")
    device_name: str = Field(alias="BROWSERSTACK_DEVICE_NAME", min_length=1)
    platform_version: str = Field(alias="BROWSERSTACK_PLATFORM_VERSION", pattern=r"^\d+(\.\d+)*$")
    timeout: int = 25

    @field_validator("username", "access_key", "app_url", "device_name", "platform_version")
    @classmethod
    def reject_placeholders(cls, value):
        text = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not text or text != text.strip() or "replace_" in text:
            raise ValueError("Fill this setting in the root .env without surrounding spaces")
        return value

    @classmethod
    def from_env_file(cls):
        # Explicit file, no environment override and no ${...} interpolation.
        values = dotenv_values(ROOT / ".env", interpolate=False)
        return cls.model_validate({field.alias: values.get(field.alias) for field in cls.model_fields.values() if field.alias})
