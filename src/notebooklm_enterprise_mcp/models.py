from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NotebookRole = Literal[
    "PROJECT_ROLE_OWNER",
    "PROJECT_ROLE_WRITER",
    "PROJECT_ROLE_READER",
    "PROJECT_ROLE_NOT_SHARED",
]

DriveDocType = Literal["doc", "slide"]
SourceKind = Literal["drive", "text", "web", "youtube"]
PodcastContextKind = Literal["text", "file"]


class NotebookShareGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., description="User email address.")
    role: NotebookRole = Field(..., description="Notebook access role.")


class SourceBatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SourceKind = Field(..., description="Source type: drive, text, web, or youtube.")
    document_id: str | None = Field(default=None, description="Google Docs or Slides document ID.")
    doc_type: DriveDocType = Field(default="doc", description="Google Drive source type.")
    text: str | None = Field(default=None, description="Raw text content.")
    url: str | None = Field(default=None, description="Web URL for web sources.")
    youtube_url: str | None = Field(default=None, description="YouTube URL for video sources.")
    display_name: str = Field(default="", description="Optional source display name.")

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "SourceBatchItem":
        if self.kind == "drive" and not self.document_id:
            raise ValueError("document_id is required when kind='drive'.")
        if self.kind == "text" and not self.text:
            raise ValueError("text is required when kind='text'.")
        if self.kind == "web" and not self.url:
            raise ValueError("url is required when kind='web'.")
        if self.kind == "youtube" and not self.youtube_url:
            raise ValueError("youtube_url is required when kind='youtube'.")
        return self


class PodcastContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: PodcastContextKind = Field(..., description="Context type: text or file.")
    text: str | None = Field(default=None, description="Text input when kind='text'.")
    file_path: str | None = Field(default=None, description="Local file path when kind='file'.")

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "PodcastContextInput":
        if self.kind == "text" and not self.text:
            raise ValueError("text is required when kind='text'.")
        if self.kind == "file" and not self.file_path:
            raise ValueError("file_path is required when kind='file'.")
        return self
