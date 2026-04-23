from __future__ import annotations
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastmcp import FastMCP

from .config import get_settings
from .backends.base import NotebookLMBackend
from .observability import LoggedBackend, configure_logging, get_logger
from .models.common import (
    NotebookShareGrant, SourceBatchItem, StudioOptions,
    PodcastContextItem, StudioArtifactType,
    AudioFormat, AudioLength, VideoFormat, VideoStyle,
    SlideFormat, SlideLength, ReportFormat, Difficulty,
    InfographicOrientation, InfographicDetail, InfographicStyle,
    ResearchSource, ResearchMode, ExportType, DriveDocType, PodcastLength,
)
from .tools import notebooks, sources, audio, studio, podcast, research, notes, exports


def _make_backend() -> NotebookLMBackend:
    cfg = get_settings()
    configure_logging(cfg)
    logger = get_logger("server")
    if cfg.mode == "enterprise":
        from .backends.enterprise import EnterpriseBackend
        backend = EnterpriseBackend()
    else:
        from .backends.web.backend import WebBackend
        backend = WebBackend()
    logger.info(
        "backend_created",
        extra={
            "event": "backend_created",
            "mode": cfg.mode,
            "backend": backend.__class__.__name__,
        },
    )
    return LoggedBackend(backend, mode=cfg.mode)  # type: ignore[return-value]


_backend: NotebookLMBackend | None = None


def get_backend() -> NotebookLMBackend:
    global _backend
    if _backend is None:
        _backend = _make_backend()
    return _backend


async def _server_startup() -> None:
    """Warm auth state and start web-mode keepalive when the server starts."""
    cfg = get_settings()
    configure_logging(cfg)
    logger = get_logger("server")
    logger.info(
        "server_startup",
        extra={
            "event": "server_startup",
            "mode": cfg.mode,
            "profile": cfg.profile if cfg.mode == "web" else None,
            "location": cfg.location if cfg.mode == "enterprise" else None,
        },
    )
    if cfg.mode == "web":
        from .auth import cookies as cookie_store
        try:
            await cookie_store.ensure_fresh()
            cookie_store.start_keepalive()
        except FileNotFoundError:
            logger.warning(
                "web_auth_missing",
                extra={"event": "web_auth_missing", "mode": cfg.mode, "profile": cfg.profile},
            )


async def _server_shutdown() -> None:
    logger = get_logger("server")
    logger.info("server_shutdown", extra={"event": "server_shutdown", "mode": get_settings().mode})
    if get_settings().mode == "web":
        from .auth import cookies as cookie_store
        cookie_store.stop_keepalive()


@asynccontextmanager
async def _server_lifespan(_server: FastMCP) -> AsyncIterator[dict]:
    await _server_startup()
    try:
        yield {}
    finally:
        await _server_shutdown()


mcp = FastMCP(
    name="notebooklm-mcp",
    instructions=(
        "MCP-сервер для NotebookLM. "
        "Режим задаётся через NOTEBOOKLM_MODE=web|enterprise. "
        "web — работает с личным аккаунтом notebooklm.google.com (auth: nlm login). "
        "enterprise — официальный REST API, требует подписку и Google Cloud проект "
        "(auth: gcloud auth application-default login или Service Account)."
    ),
    lifespan=_server_lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# Ноутбуки
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def notebook_create(title: str) -> dict:
    """Создать новый ноутбук."""
    return await notebooks.notebook_create(get_backend(), title)


@mcp.tool()
async def notebook_get(notebook_id: str) -> dict:
    """Получить детали ноутбука (заголовок, источники, статус шаринга)."""
    return await notebooks.notebook_get(get_backend(), notebook_id)


@mcp.tool()
async def notebook_list(page_size: int = 100) -> dict:
    """Список недавних ноутбуков (максимум 500)."""
    return await notebooks.notebook_list(get_backend(), page_size)


@mcp.tool()
async def notebook_delete(notebook_ids: list[str]) -> dict:
    """Удалить один или несколько ноутбуков по ID."""
    return await notebooks.notebook_delete(get_backend(), notebook_ids)


@mcp.tool()
async def notebook_rename(notebook_id: str, new_title: str) -> dict:
    """Переименовать ноутбук. Только в web режиме."""
    return await notebooks.notebook_rename(get_backend(), notebook_id, new_title)


@mcp.tool()
async def notebook_describe(notebook_id: str) -> dict:
    """AI-описание ноутбука и предлагаемые темы. Только в web режиме."""
    return await notebooks.notebook_describe(get_backend(), notebook_id)


@mcp.tool()
async def notebook_share(
    notebook_id: str,
    grants: list[NotebookShareGrant],
) -> dict:
    """
    Поделиться ноутбуком с пользователями.

    В enterprise режиме роли: PROJECT_ROLE_OWNER / WRITER / READER / NOT_SHARED.
    В web режиме роли: PROJECT_ROLE_WRITER (editor) / PROJECT_ROLE_READER (viewer) / NOT_SHARED.
    """
    return await notebooks.notebook_share(
        get_backend(), notebook_id, [g.model_dump() for g in grants]
    )


@mcp.tool()
async def notebook_share_public(notebook_id: str, is_public: bool = True) -> dict:
    """Включить/выключить публичный доступ по ссылке. Только в web режиме."""
    return await notebooks.notebook_share_public(get_backend(), notebook_id, is_public)


@mcp.tool()
async def notebook_share_status(notebook_id: str) -> dict:
    """Текущие настройки доступа к ноутбуку. Только в web режиме."""
    return await notebooks.notebook_share_status(get_backend(), notebook_id)


# ─────────────────────────────────────────────────────────────────────────────
# Источники
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def source_add_url(
    notebook_id: str,
    url: str,
    display_name: str = "",
) -> dict:
    """Добавить веб-страницу как источник."""
    return await sources.source_add_url(get_backend(), notebook_id, url, display_name)


@mcp.tool()
async def source_add_urls(notebook_id: str, urls: list[str]) -> dict:
    """Добавить несколько URL за один запрос."""
    return await sources.source_add_urls(get_backend(), notebook_id, urls)


@mcp.tool()
async def source_add_text(
    notebook_id: str, text: str, title: str = ""
) -> dict:
    """Добавить plain text как источник."""
    return await sources.source_add_text(get_backend(), notebook_id, text, title)


@mcp.tool()
async def source_add_drive(
    notebook_id: str,
    document_id: str,
    doc_type: DriveDocType = "doc",
    display_name: str = "",
) -> dict:
    """
    Добавить Google Drive документ как источник.

    doc_type: 'doc' (Google Docs) | 'slide' (Google Slides)
    document_id: ID документа из URL Google Drive
    """
    return await sources.source_add_drive(
        get_backend(), notebook_id, document_id, doc_type, display_name
    )


@mcp.tool()
async def source_add_youtube(notebook_id: str, youtube_url: str) -> dict:
    """Добавить YouTube-видео как источник."""
    return await sources.source_add_youtube(get_backend(), notebook_id, youtube_url)


@mcp.tool()
async def source_add_batch(
    notebook_id: str, items: list[SourceBatchItem]
) -> dict:
    """Добавить смешанный набор источников за один запрос."""
    return await sources.source_add_batch(get_backend(), notebook_id, items)


@mcp.tool()
async def source_upload_file(
    notebook_id: str, file_path: str, display_name: str = ""
) -> dict:
    """
    Загрузить локальный файл как источник.

    Поддерживаемые форматы: PDF, DOCX, PPTX, XLSX, TXT, MD, MP3, MP4, PNG, JPG и др.
    """
    return await sources.source_upload_file(
        get_backend(), notebook_id, file_path, display_name
    )


@mcp.tool()
async def source_get(notebook_id: str, source_id: str) -> dict:
    """Получить детали источника (статус обработки, количество слов)."""
    return await sources.source_get(get_backend(), notebook_id, source_id)


@mcp.tool()
async def source_delete(notebook_id: str, source_ids: list[str]) -> dict:
    """Удалить один или несколько источников из ноутбука."""
    return await sources.source_delete(get_backend(), notebook_id, source_ids)


@mcp.tool()
async def source_rename(
    notebook_id: str, source_id: str, new_title: str
) -> dict:
    """Переименовать источник. Только в web режиме."""
    return await sources.source_rename(get_backend(), notebook_id, source_id, new_title)


@mcp.tool()
async def source_sync_drive(source_ids: list[str]) -> dict:
    """Синхронизировать Drive-источники с актуальным содержимым. Только в web режиме."""
    return await sources.source_sync_drive(get_backend(), source_ids)


@mcp.tool()
async def source_describe(source_id: str) -> dict:
    """AI-описание источника и ключевые слова. Только в web режиме."""
    return await sources.source_describe(get_backend(), source_id)


# ─────────────────────────────────────────────────────────────────────────────
# Аудио-обзор
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def audio_overview_create(
    notebook_id: str,
    source_ids: list[str] | None = None,
    episode_focus: str = "",
    language_code: str = "en",
) -> dict:
    """
    Создать аудио-обзор (подкаст) из источников ноутбука.

    - source_ids: конкретные источники; если пусто — используются все
    - episode_focus: тема для акцента
    - language_code: BCP47 код языка (en, ru, de, ...)
    """
    return await audio.audio_overview_create(
        get_backend(), notebook_id, source_ids, episode_focus, language_code
    )


@mcp.tool()
async def audio_overview_delete(notebook_id: str) -> dict:
    """Удалить аудио-обзор ноутбука."""
    return await audio.audio_overview_delete(get_backend(), notebook_id)


# ─────────────────────────────────────────────────────────────────────────────
# Studio (только web режим)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def studio_create(
    notebook_id: str,
    artifact_type: StudioArtifactType,
    source_ids: list[str] = [],
    # audio
    audio_format: AudioFormat = "deep_dive",
    audio_length: AudioLength = "default",
    focus_prompt: str = "",
    language_code: str = "en",
    # video
    video_format: VideoFormat = "explainer",
    visual_style: VideoStyle = "auto_select",
    # slide_deck
    slide_format: SlideFormat = "detailed_deck",
    slide_length: SlideLength = "default",
    # report
    report_format: ReportFormat = "Briefing Doc",
    custom_prompt: str = "",
    # flashcards / quiz
    difficulty: Difficulty = "medium",
    question_count: int = 10,
    # infographic
    orientation: InfographicOrientation = "landscape",
    detail_level: InfographicDetail = "standard",
    infographic_style: InfographicStyle = "auto_select",
    # data_table
    description: str = "",
    # mind_map
    title: str = "",
) -> dict:
    """
    Создать Studio артефакт. Только в web режиме.

    artifact_type: audio | video | report | flashcards | quiz |
                   infographic | slide_deck | data_table | mind_map
    """
    opts = StudioOptions(
        source_ids=source_ids,
        audio_format=audio_format,
        audio_length=audio_length,
        focus_prompt=focus_prompt,
        language_code=language_code,
        video_format=video_format,
        visual_style=visual_style,
        slide_format=slide_format,
        slide_length=slide_length,
        report_format=report_format,
        custom_prompt=custom_prompt,
        difficulty=difficulty,
        question_count=question_count,
        orientation=orientation,
        detail_level=detail_level,
        infographic_style=infographic_style,
        description=description,
        title=title,
    )
    return await studio.studio_create(get_backend(), notebook_id, artifact_type, opts)


@mcp.tool()
async def studio_status(notebook_id: str) -> dict:
    """Статус всех Studio артефактов ноутбука. Только в web режиме."""
    return await studio.studio_status(get_backend(), notebook_id)


@mcp.tool()
async def studio_delete(notebook_id: str, artifact_id: str) -> dict:
    """Удалить Studio артефакт. Только в web режиме."""
    return await studio.studio_delete(get_backend(), notebook_id, artifact_id)


@mcp.tool()
async def studio_revise(
    notebook_id: str,
    artifact_id: str,
    slide_instructions: list[dict],
) -> dict:
    """Пересмотреть отдельные слайды в существующем слайд-деке. Только в web режиме."""
    return await studio.studio_revise(
        get_backend(), notebook_id, artifact_id, slide_instructions
    )


# ─────────────────────────────────────────────────────────────────────────────
# Чат / Запросы (только web режим)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def notebook_query(
    notebook_id: str,
    query: str,
    source_ids: list[str] | None = None,
    conversation_id: str | None = None,
) -> dict:
    """
    Задать вопрос по источникам ноутбука. Только в web режиме.

    - conversation_id: для продолжения диалога (из предыдущего ответа)
    """
    from .backends.base import NotebookLMBackend
    get_backend().require("query", "notebook_query")
    return await get_backend().notebook_query(
        notebook_id, query, source_ids, conversation_id
    )


# ─────────────────────────────────────────────────────────────────────────────
# Исследования (только web режим)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def research_start(
    notebook_id: str,
    query: str,
    source: ResearchSource = "web",
    mode: ResearchMode = "fast",
) -> dict:
    """
    Запустить поиск новых источников. Только в web режиме.

    source: 'web' | 'drive'
    mode: 'fast' | 'deep'
    Возвращает taskId для опроса через research_status.
    """
    return await research.research_start(get_backend(), notebook_id, query, source, mode)


@mcp.tool()
async def research_status(notebook_id: str, task_id: str) -> dict:
    """Проверить статус исследования. Только в web режиме."""
    return await research.research_status(get_backend(), notebook_id, task_id)


@mcp.tool()
async def research_import(
    notebook_id: str,
    task_id: str,
    source_indices: list[int] | None = None,
) -> dict:
    """Импортировать найденные источники в ноутбук. Только в web режиме."""
    return await research.research_import(
        get_backend(), notebook_id, task_id, source_indices
    )


# ─────────────────────────────────────────────────────────────────────────────
# Заметки (только web режим)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def note_create(
    notebook_id: str, content: str, title: str = ""
) -> dict:
    """Создать заметку в ноутбуке. Только в web режиме."""
    return await notes.note_create(get_backend(), notebook_id, content, title)


@mcp.tool()
async def note_list(notebook_id: str) -> dict:
    """Список заметок ноутбука. Только в web режиме."""
    return await notes.note_list(get_backend(), notebook_id)


@mcp.tool()
async def note_update(
    notebook_id: str, note_id: str, content: str, title: str = ""
) -> dict:
    """Обновить заметку. Только в web режиме."""
    return await notes.note_update(get_backend(), notebook_id, note_id, content, title)


@mcp.tool()
async def note_delete(notebook_id: str, note_id: str) -> dict:
    """Удалить заметку. Только в web режиме."""
    return await notes.note_delete(get_backend(), notebook_id, note_id)


# ─────────────────────────────────────────────────────────────────────────────
# Экспорт / Загрузка (только web режим)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def export_artifact(
    notebook_id: str,
    artifact_id: str,
    export_type: ExportType,
    title: str = "",
) -> dict:
    """Экспортировать артефакт в Google Docs или Sheets. Только в web режиме."""
    return await exports.export_artifact(
        get_backend(), notebook_id, artifact_id, export_type, title
    )


@mcp.tool()
async def download_artifact(
    notebook_id: str,
    artifact_type: str,
    output_path: str,
    artifact_id: str | None = None,
) -> dict:
    """Скачать артефакт в локальный файл. Только в web режиме."""
    return await exports.download_artifact(
        get_backend(), notebook_id, artifact_type, output_path, artifact_id
    )


# ─────────────────────────────────────────────────────────────────────────────
# Podcast API (только enterprise режим)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def podcast_create(
    focus: str,
    length: PodcastLength = "STANDARD",
    texts: list[str] | None = None,
    file_paths: list[str] | None = None,
    title: str = "",
    description: str = "",
    language_code: str = "en",
) -> dict:
    """
    Создать подкаст без ноутбука (standalone Podcast API). Только в enterprise режиме.

    - focus: тема подкаста
    - length: 'SHORT' (~4-5 мин) | 'STANDARD' (~10 мин)
    - texts: список текстовых фрагментов как контекст
    - file_paths: локальные файлы как контекст (PDF, DOCX, MP3, ...)
    - Итого контекст < 100 000 токенов
    - Возвращает operation_name для podcast_download
    """
    return await podcast.podcast_create(
        get_backend(), focus, length, texts, file_paths, title, description, language_code
    )


@mcp.tool()
async def podcast_download(operation_name: str, output_path: str) -> str:
    """
    Скачать готовый подкаст MP3. Только в enterprise режиме.

    - operation_name: поле 'name' из ответа podcast_create
    - output_path: путь для сохранения MP3
    """
    return await podcast.podcast_download(get_backend(), operation_name, output_path)


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def save_auth_tokens(
    cookies_json: str,
    csrf_token: str = "",
    session_id: str = "",
    build_label: str = "",
) -> dict:
    """
    Сохранить Google cookies вручную (резервный метод для web режима).

    cookies_json: JSON-строка с cookies, например:
        {"SID": "...", "HSID": "...", "SSID": "...", "APISID": "...", "SAPISID": "..."}
    """
    import json
    import time
    from .auth import cookies as cookie_store
    from .auth.cookies import AuthTokens

    try:
        cookies = json.loads(cookies_json)
    except json.JSONDecodeError as e:
        return {"error": f"Некорректный JSON: {e}"}

    tokens = AuthTokens(
        cookies=cookies,
        csrf_token=csrf_token,
        session_id=session_id,
        build_label=build_label or cookie_store._BUILD_FALLBACK,
        extracted_at=time.time(),
    )
    cookie_store.set_tokens(tokens)
    return {"status": "ok", "profile": get_settings().profile}


@mcp.tool()
async def refresh_auth() -> dict:
    """Обновить CSRF и session токены (web режим) или проверить Google Cloud auth."""
    cfg = get_settings()
    logger = get_logger("auth")
    logger.info("auth_refresh_start", extra={"event": "auth_refresh_start", "mode": cfg.mode})
    if cfg.mode == "web":
        from .auth import cookies as cookie_store
        tokens = cookie_store.get_tokens()
        tokens = await cookie_store.refresh_page_tokens(tokens)
        cookie_store.set_tokens(tokens)
        result = {"status": "ok", "csrf_refreshed": bool(tokens.csrf_token)}
        logger.info(
            "auth_refresh_success",
            extra={"event": "auth_refresh_success", "mode": cfg.mode, "csrf_refreshed": result["csrf_refreshed"]},
        )
        return result
    from .auth.gcloud import get_access_token
    token = get_access_token()
    logger.info("auth_refresh_success", extra={"event": "auth_refresh_success", "mode": cfg.mode})
    return {"status": "ok", "token_prefix": token[:10] + "..."}


@mcp.tool()
async def server_info() -> dict:
    """Информация о сервере: версия, режим, профиль."""
    cfg = get_settings()
    return {
        "version": "0.1.0",
        "mode": cfg.mode,
        "profile": cfg.profile if cfg.mode == "web" else None,
        "location": cfg.location if cfg.mode == "enterprise" else None,
    }


def main() -> None:
    configure_logging()
    mcp.run()


if __name__ == "__main__":
    main()
