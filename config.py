"""UI/API settings and explicitly enabled Selenoid configuration."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("BASE_URL", "https://automationexercise.com").rstrip("/")
    ui_timeout: int = 15
    api_timeout: tuple[int, int] = (10, 30)


settings = Settings()


class SelenoidSettings(BaseModel):
    """Loaded only for an explicitly selected remote UI session."""

    model_config = ConfigDict(strict=True, frozen=True, hide_input_in_errors=True)

    webdriver_url: str = Field(alias="SELENOID_URL", validation_alias=AliasChoices("SELENOID_URL", "SELENOID_WEBDRIVER_URL"), repr=False)
    browser_version: str = Field(alias="SELENOID_BROWSER_VERSION", min_length=1)
    video_base_url: str = Field(alias="SELENOID_VIDEO_BASE_URL", repr=False)
    username: SecretStr | None = Field(default=None, alias="SELENOID_LOGIN", validation_alias=AliasChoices("SELENOID_LOGIN", "SELENOID_USERNAME"), repr=False)
    password: SecretStr | None = Field(default=None, alias="SELENOID_PASS", validation_alias=AliasChoices("SELENOID_PASS", "SELENOID_PASSWORD"), repr=False)
    video_username: SecretStr | None = Field(default=None, alias="SELENOID_VIDEO_USERNAME", repr=False)
    video_password: SecretStr | None = Field(default=None, alias="SELENOID_VIDEO_PASSWORD", repr=False)

    @field_validator("webdriver_url", mode="before")
    @classmethod
    def normalize_webdriver_url(cls, value):
        if not isinstance(value, str):
            return value
        cls.reject_placeholders(value)
        # A bare course hostname uses HTTPS. An explicit scheme/path is preserved.
        if "://" not in value:
            value = "https://" + value
        value = cls.require_clean_url(value)
        path = urlsplit(value).path.rstrip("/")
        if path.count("/wd/hub") > 1:
            raise ValueError("Duplicated WebDriver path")
        return value + "/wd/hub" if not path else value

    @field_validator("webdriver_url", "video_base_url", "browser_version")
    @classmethod
    def reject_placeholders(cls, value):
        if not value or value != value.strip() or any(c.isspace() for c in value) or "replace" in value.lower():
            raise ValueError("Fill this setting without placeholders or whitespace")
        return value

    @field_validator("webdriver_url", "video_base_url")
    @classmethod
    def require_clean_url(cls, value):
        url = urlsplit(value)
        if (url.scheme not in ("http", "https") or not url.hostname or url.username is not None
                or url.password is not None or url.query or url.fragment):
            raise ValueError("Use an HTTP(S) URL without credentials, query or fragment")
        try:
            url.port
        except ValueError:
            raise ValueError("Invalid URL port") from None
        return value.rstrip("/")

    @field_validator("username", "password", "video_username", "video_password")
    @classmethod
    def validate_secret(cls, value):
        if value is not None:
            text = value.get_secret_value()
            if not text or text != text.strip() or "replace" in text.lower():
                raise ValueError("Use a real credential without surrounding whitespace, or leave both fields empty")
        return value

    @model_validator(mode="after")
    def require_auth_pairs(self):
        if bool(self.username) != bool(self.password) or bool(self.video_username) != bool(self.video_password):
            raise ValueError("Fill both username/password fields for each endpoint, or leave both empty")
        return self

    @classmethod
    def from_env_file(cls):
        # Same explicit-file policy as Mobile: no process override/interpolation.
        values = dotenv_values(ROOT / ".env", interpolate=False)
        selected = {}
        for field in cls.model_fields.values():
            aliases = (field.validation_alias.choices if isinstance(field.validation_alias, AliasChoices)
                       else [field.alias])
            configured = [values[key] for key in aliases if values.get(key)]
            if len(set(configured)) > 1:
                raise ValueError(f"Conflicting settings for {field.alias}; keep one value")
            selected[field.alias] = configured[0] if configured else None
        return cls.model_validate(selected)
