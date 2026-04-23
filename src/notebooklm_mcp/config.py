from __future__ import annotations
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOTEBOOKLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Режим ────────────────────────────────────────────────────────────────
    mode: Literal["web", "enterprise"] = Field(
        default="web",
        description="Режим работы: 'web' (notebooklm.google.com) или 'enterprise' (REST API)",
    )

    # ── Enterprise ───────────────────────────────────────────────────────────
    project_number: str | None = Field(
        default=None,
        description="Номер Google Cloud проекта (для Enterprise режима)",
    )
    project_id: str | None = Field(
        default=None,
        description="ID Google Cloud проекта (для Podcast API)",
    )
    location: str = Field(default="global", description="us | eu | global")
    endpoint_location: str = Field(default="global", description="us | eu | global")

    # ── Auth (Enterprise) ────────────────────────────────────────────────────
    google_application_credentials: str | None = Field(
        default=None,
        description="Путь к Service Account JSON ключу",
    )
    use_gcloud_token: bool = Field(
        default=False,
        description="Использовать gcloud auth print-access-token вместо ADC",
    )

    # ── Auth (Web) ────────────────────────────────────────────────────────────
    profile: str = Field(
        default="default",
        description="Имя профиля (папка с cookies)",
    )
    auth_dir: str = Field(
        default="~/.notebooklm-mcp-cli",
        description="Директория хранения cookies (совместима с nlm)",
    )
    language: str = Field(default="en", description="Язык UI (BCP47 код)")

    # ── Сеть ─────────────────────────────────────────────────────────────────
    timeout: int = Field(default=120, description="Таймаут запросов (сек)")
    max_retries: int = Field(default=3, description="Макс. повторы при ошибках")

    # ── Logging / observability ──────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR")
    log_file: str | None = Field(
        default="logs/notebooklm-mcp.log",
        description="Path to a log file. Empty value disables file logging.",
    )
    log_to_console: bool = Field(default=True, description="Also write logs to stderr")
    log_format: Literal["text", "json"] = Field(default="text", description="Log format")
    log_arguments: bool = Field(
        default=False,
        description="Log sanitized call arguments. Disabled by default to avoid leaking source text.",
    )
    log_max_value_length: int = Field(default=160, description="Max length for logged values")

    @field_validator("project_number", mode="before")
    @classmethod
    def _require_project_number_for_enterprise(cls, v: str | None) -> str | None:
        return v

    @field_validator("log_file", mode="before")
    @classmethod
    def _empty_log_file_to_none(cls, v: str | None) -> str | None:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: str | None) -> str:
        return (v or "INFO").upper()

    @property
    def auth_dir_path(self) -> Path:
        return Path(self.auth_dir).expanduser()

    @property
    def profile_dir(self) -> Path:
        return self.auth_dir_path / "profiles" / self.profile

    @property
    def log_file_path(self) -> Path | None:
        if not self.log_file:
            return None
        return Path(self.log_file).expanduser()

    # ── Enterprise URL helpers ────────────────────────────────────────────────
    @property
    def _base_url(self) -> str:
        num = self.project_number or ""
        return (
            f"https://{self.endpoint_location}-discoveryengine.googleapis.com"
            f"/v1alpha/projects/{num}/locations/{self.location}"
        )

    @property
    def notebooks_url(self) -> str:
        return f"{self._base_url}/notebooks"

    def notebook_url(self, notebook_id: str) -> str:
        return f"{self.notebooks_url}/{notebook_id}"

    def sources_url(self, notebook_id: str) -> str:
        return f"{self.notebook_url(notebook_id)}/sources"

    def source_url(self, notebook_id: str, source_id: str) -> str:
        return f"{self.sources_url(notebook_id)}/{source_id}"

    def source_upload_url(self, notebook_id: str) -> str:
        num = self.project_number or ""
        return (
            f"https://{self.endpoint_location}-discoveryengine.googleapis.com"
            f"/upload/v1alpha/projects/{num}/locations/{self.location}"
            f"/notebooks/{notebook_id}/sources:uploadFile"
        )

    def audio_overviews_url(self, notebook_id: str) -> str:
        return f"{self.notebook_url(notebook_id)}/audioOverviews"

    @property
    def podcasts_url(self) -> str:
        project = self.project_id or self.project_number or ""
        return f"https://discoveryengine.googleapis.com/v1/projects/{project}/locations/global/podcasts"

    def notebook_name(self, notebook_id: str) -> str:
        num = self.project_number or ""
        return f"projects/{num}/locations/{self.location}/notebooks/{notebook_id}"

    def source_name(self, notebook_id: str, source_id: str) -> str:
        num = self.project_number or ""
        return (
            f"projects/{num}/locations/{self.location}"
            f"/notebooks/{notebook_id}/source/{source_id}"
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
