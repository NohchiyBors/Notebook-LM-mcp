from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOTEBOOKLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_number: str = Field(
        ...,
        description="Google Cloud project number (not project ID)",
    )
    project_id: str | None = Field(
        default=None,
        description=(
            "Google Cloud project ID for standalone Podcast API calls. "
            "Official docs currently use PROJECT_ID for /v1/projects/{project}/locations/global/podcasts."
        ),
    )
    location: str = Field(
        default="global",
        description="Data store location: us, eu, or global",
    )
    endpoint_location: str = Field(
        default="global",
        description="API endpoint location: us, eu, or global",
    )
    google_application_credentials: str | None = Field(
        default=None,
        description="Path to service account JSON key file (optional, uses ADC if not set)",
    )
    use_gcloud_access_token: bool = Field(
        default=False,
        description=(
            "If true, call `gcloud auth print-access-token` for every request. "
            "Useful for Google Drive-backed sources that require a user login with Drive access."
        ),
    )

    @property
    def base_url(self) -> str:
        return (
            f"https://{self.endpoint_location}-discoveryengine.googleapis.com"
            f"/v1alpha/projects/{self.project_number}/locations/{self.location}"
        )

    @property
    def notebooks_url(self) -> str:
        return f"{self.base_url}/notebooks"

    def notebook_url(self, notebook_id: str) -> str:
        return f"{self.notebooks_url}/{notebook_id}"

    def sources_url(self, notebook_id: str) -> str:
        return f"{self.notebook_url(notebook_id)}/sources"

    def source_url(self, notebook_id: str, source_id: str) -> str:
        return f"{self.sources_url(notebook_id)}/{source_id}"

    def source_upload_url(self, notebook_id: str) -> str:
        return (
            f"https://{self.endpoint_location}-discoveryengine.googleapis.com"
            f"/upload/v1alpha/projects/{self.project_number}/locations/{self.location}"
            f"/notebooks/{notebook_id}/sources:uploadFile"
        )

    def audio_overviews_url(self, notebook_id: str) -> str:
        return f"{self.notebook_url(notebook_id)}/audioOverviews"

    @property
    def podcasts_url(self) -> str:
        project = self.project_id or self.project_number
        return f"https://discoveryengine.googleapis.com/v1/projects/{project}/locations/global/podcasts"

    def notebook_name(self, notebook_id: str) -> str:
        return (
            f"projects/{self.project_number}/locations/{self.location}"
            f"/notebooks/{notebook_id}"
        )

    def source_name(self, notebook_id: str, source_id: str) -> str:
        return (
            f"projects/{self.project_number}/locations/{self.location}"
            f"/notebooks/{notebook_id}/source/{source_id}"
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
