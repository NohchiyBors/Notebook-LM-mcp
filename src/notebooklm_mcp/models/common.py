from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


# ── Notebooks ─────────────────────────────────────────────────────────────────

NotebookRole = Literal[
    "PROJECT_ROLE_OWNER",
    "PROJECT_ROLE_WRITER",
    "PROJECT_ROLE_READER",
    "PROJECT_ROLE_NOT_SHARED",
]

WebShareRole = Literal["viewer", "editor"]

DriveDocType = Literal["doc", "slide"]

PodcastLength = Literal["SHORT", "STANDARD"]

StudioArtifactType = Literal[
    "audio", "video", "report", "flashcards", "quiz",
    "infographic", "slide_deck", "data_table", "mind_map",
]

AudioFormat = Literal["deep_dive", "brief", "critique", "debate"]
AudioLength = Literal["short", "default", "long"]

VideoFormat = Literal["explainer", "brief"]
VideoStyle = Literal[
    "auto_select", "classic", "whiteboard", "kawaii", "anime",
    "watercolor", "retro_print", "heritage", "paper_craft",
]

SlideFormat = Literal["detailed_deck", "presenter_slides"]
SlideLength = Literal["short", "default"]

ReportFormat = Literal["Briefing Doc", "Study Guide", "Blog Post", "Create Your Own"]

Difficulty = Literal["easy", "medium", "hard"]

InfographicOrientation = Literal["landscape", "portrait", "square"]
InfographicDetail = Literal["concise", "standard", "detailed"]
InfographicStyle = Literal[
    "auto_select", "sketch_note", "professional", "bento_grid",
    "editorial", "instructional", "bricks", "clay", "anime",
    "kawaii", "scientific",
]

ResearchSource = Literal["web", "drive"]
ResearchMode = Literal["fast", "deep"]

ExportType = Literal["docs", "sheets"]


class NotebookShareGrant(BaseModel):
    email: str
    role: NotebookRole


class SourceBatchItem(BaseModel):
    """Один элемент для batch-добавления источников."""
    kind: Literal["web", "text", "drive", "youtube"]
    url: str = ""
    text: str = ""
    document_id: str = ""
    doc_type: DriveDocType = "doc"
    youtube_url: str = ""
    display_name: str = ""


class PodcastContextItem(BaseModel):
    """Один элемент контекста для Podcast API."""
    kind: Literal["text", "file"]
    text: str = ""
    file_path: str = ""


class StudioOptions(BaseModel):
    """Опции для studio_create (type-specific поля опциональны)."""
    source_ids: list[str] = []

    # audio
    audio_format: AudioFormat = "deep_dive"
    audio_length: AudioLength = "default"
    focus_prompt: str = ""
    language_code: str = "en"

    # video
    video_format: VideoFormat = "explainer"
    visual_style: VideoStyle = "auto_select"

    # slide_deck
    slide_format: SlideFormat = "detailed_deck"
    slide_length: SlideLength = "default"

    # report
    report_format: ReportFormat = "Briefing Doc"
    custom_prompt: str = ""

    # flashcards / quiz
    difficulty: Difficulty = "medium"
    question_count: int = 10

    # infographic
    orientation: InfographicOrientation = "landscape"
    detail_level: InfographicDetail = "standard"
    infographic_style: InfographicStyle = "auto_select"

    # data_table
    description: str = ""

    # mind_map
    title: str = ""
