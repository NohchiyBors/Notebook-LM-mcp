"""Константы RPC ID и вспомогательные функции для batchexecute протокола."""
from __future__ import annotations

# ── Notebooks ────────────────────────────────────────────────────────────────
RPC_NOTEBOOK_LIST   = "wXbhsf"
RPC_NOTEBOOK_GET    = "rLM1Ne"
RPC_NOTEBOOK_CREATE = "CCqFvf"
RPC_NOTEBOOK_RENAME = "s0tc2d"
RPC_NOTEBOOK_DELETE = "WWINqb"
RPC_NOTEBOOK_DESCRIBE = "VfAZjd"

# ── Sources ──────────────────────────────────────────────────────────────────
RPC_SOURCE_ADD          = "izAoDd"
RPC_SOURCE_FILE_INIT    = "o4cbdc"   # регистрация файла перед upload
RPC_SOURCE_GET          = "hizoJc"
RPC_SOURCE_DELETE       = "tGMBJ"
RPC_SOURCE_RENAME       = "b7Wfje"
RPC_SOURCE_SYNC_DRIVE   = "FLmJqe"
RPC_SOURCE_CHECK_FRESH  = "yR9Yof"
RPC_SOURCE_DESCRIBE     = "tr032e"

# ── Studio ───────────────────────────────────────────────────────────────────
RPC_STUDIO_CREATE       = "R7cb6c"
RPC_STUDIO_POLL         = "gArtLc"
RPC_STUDIO_DELETE       = "V5N4be"
RPC_STUDIO_RENAME       = "rc3d8d"
RPC_STUDIO_REVISE_SLIDES = "KmcKPe"
RPC_MIND_MAP_GENERATE   = "yyryJe"
RPC_MIND_MAP_SAVE       = "CYK0Xb"
RPC_MIND_MAP_LIST       = "cFji9"
RPC_MIND_MAP_DELETE     = "AH0mwd"
RPC_INTERACTIVE_HTML    = "v9rmvd"

# ── Research ─────────────────────────────────────────────────────────────────
RPC_RESEARCH_FAST   = "Ljjv0c"
RPC_RESEARCH_DEEP   = "QA9ei"
RPC_RESEARCH_POLL   = "e3bVqc"
RPC_RESEARCH_IMPORT = "LBwxtb"

# ── Notes ────────────────────────────────────────────────────────────────────
RPC_NOTE_CREATE = "CYK0Xb"
RPC_NOTE_LIST   = "cFji9"
RPC_NOTE_UPDATE = "cYAfTb"
RPC_NOTE_DELETE = "AH0mwd"

# ── Sharing ──────────────────────────────────────────────────────────────────
RPC_SHARE_SET    = "QDyure"
RPC_SHARE_STATUS = "JFMDGd"

# ── Exports ──────────────────────────────────────────────────────────────────
RPC_EXPORT = "Krh3pd"

# ── Studio type codes ────────────────────────────────────────────────────────
STUDIO_TYPE = {
    "audio":      1,
    "report":     2,
    "video":      3,
    "flashcards": 4,
    "quiz":       4,
    "infographic":7,
    "slide_deck": 8,
    "data_table": 9,
}

# ── Audio format/length codes ────────────────────────────────────────────────
AUDIO_FORMAT_CODE = {"deep_dive": 1, "brief": 2, "critique": 3, "debate": 4}
AUDIO_LENGTH_CODE = {"short": 1, "default": 2, "long": 3}

# ── Video style codes ─────────────────────────────────────────────────────────
VIDEO_STYLE_CODE = {
    "auto_select": 0, "classic": 1, "whiteboard": 2, "kawaii": 3,
    "anime": 4, "watercolor": 5, "retro_print": 6, "heritage": 7,
    "paper_craft": 8,
}
VIDEO_FORMAT_CODE = {"explainer": 1, "brief": 2}

# ── Slide format/length codes ─────────────────────────────────────────────────
SLIDE_FORMAT_CODE  = {"detailed_deck": 1, "presenter_slides": 2}
SLIDE_LENGTH_CODE  = {"short": 1, "default": 2}

# ── Report format codes ───────────────────────────────────────────────────────
REPORT_FORMAT_CODE = {
    "Briefing Doc": 1, "Study Guide": 2, "Blog Post": 3, "Create Your Own": 4,
}

# ── Difficulty codes ──────────────────────────────────────────────────────────
DIFFICULTY_CODE = {"easy": 1, "medium": 2, "hard": 3}

# ── Research codes ────────────────────────────────────────────────────────────
RESEARCH_SOURCE_CODE = {"web": 1, "drive": 2}
RESEARCH_MODE_CODE   = {"fast": 1, "deep": 5}

# ── Drive MIME types ──────────────────────────────────────────────────────────
DRIVE_MIME = {
    "doc":   "application/vnd.google-apps.document",
    "slide": "application/vnd.google-apps.presentation",
}

# ── Studio status codes ───────────────────────────────────────────────────────
STUDIO_STATUS = {1: "in_progress", 3: "completed", 4: "failed"}
