from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class NotebookLMBackend(ABC):
    """Абстрактный интерфейс backend-адаптера."""

    # Набор поддерживаемых фич — переопределяется в подклассах
    _features: frozenset[str] = frozenset()

    def supports(self, feature: str) -> bool:
        return feature in self._features

    def require(self, feature: str, tool_name: str) -> None:
        """Бросает RuntimeError с понятным сообщением если фича недоступна."""
        if not self.supports(feature):
            mode = self.__class__.__name__.replace("Backend", "").lower()
            raise NotImplementedError(
                f"'{tool_name}' недоступен в режиме '{mode}'. "
                f"Переключитесь на режим 'web' для доступа к этой функции."
                if mode == "enterprise"
                else f"'{tool_name}' недоступен в режиме '{mode}'."
            )

    # ── Notebooks ────────────────────────────────────────────────────────────

    @abstractmethod
    async def notebook_create(self, title: str) -> dict: ...

    @abstractmethod
    async def notebook_get(self, notebook_id: str) -> dict: ...

    @abstractmethod
    async def notebook_list(self, page_size: int = 100) -> dict: ...

    @abstractmethod
    async def notebook_delete(self, notebook_ids: list[str]) -> dict: ...

    @abstractmethod
    async def notebook_share(
        self, notebook_id: str, grants: list[dict]
    ) -> dict: ...

    async def notebook_rename(self, notebook_id: str, new_title: str) -> dict:
        self.require("notebook_rename", "notebook_rename")
        raise NotImplementedError

    async def notebook_describe(self, notebook_id: str) -> dict:
        self.require("notebook_describe", "notebook_describe")
        raise NotImplementedError

    # ── Sources ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def source_add(
        self, notebook_id: str, user_contents: list[dict]
    ) -> dict: ...

    @abstractmethod
    async def source_upload_file(
        self, notebook_id: str, file_path: str, display_name: str
    ) -> dict: ...

    @abstractmethod
    async def source_get(self, notebook_id: str, source_id: str) -> dict: ...

    @abstractmethod
    async def source_delete(
        self, notebook_id: str, source_ids: list[str]
    ) -> dict: ...

    async def source_rename(
        self, notebook_id: str, source_id: str, new_title: str
    ) -> dict:
        self.require("source_rename", "source_rename")
        raise NotImplementedError

    async def source_sync_drive(self, source_ids: list[str]) -> dict:
        self.require("source_sync_drive", "source_sync_drive")
        raise NotImplementedError

    async def source_describe(self, source_id: str) -> dict:
        self.require("source_describe", "source_describe")
        raise NotImplementedError

    # ── Audio Overview ───────────────────────────────────────────────────────

    @abstractmethod
    async def audio_overview_create(
        self,
        notebook_id: str,
        source_ids: list[str] | None,
        episode_focus: str,
        language_code: str,
    ) -> dict: ...

    @abstractmethod
    async def audio_overview_delete(self, notebook_id: str) -> dict: ...

    # ── Studio (web only) ────────────────────────────────────────────────────

    async def studio_create(
        self, notebook_id: str, artifact_type: str, **kwargs: Any
    ) -> dict:
        self.require("studio", "studio_create")
        raise NotImplementedError

    async def studio_status(self, notebook_id: str) -> dict:
        self.require("studio", "studio_status")
        raise NotImplementedError

    async def studio_delete(
        self, notebook_id: str, artifact_id: str
    ) -> dict:
        self.require("studio", "studio_delete")
        raise NotImplementedError

    async def studio_revise(
        self,
        notebook_id: str,
        artifact_id: str,
        slide_instructions: list[dict],
    ) -> dict:
        self.require("studio", "studio_revise")
        raise NotImplementedError

    # ── Query (web only) ─────────────────────────────────────────────────────

    async def notebook_query(
        self,
        notebook_id: str,
        query: str,
        source_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        self.require("query", "notebook_query")
        raise NotImplementedError

    # ── Research (web only) ──────────────────────────────────────────────────

    async def research_start(
        self,
        notebook_id: str,
        query: str,
        source: str,
        mode: str,
    ) -> dict:
        self.require("research", "research_start")
        raise NotImplementedError

    async def research_status(self, notebook_id: str, task_id: str) -> dict:
        self.require("research", "research_status")
        raise NotImplementedError

    async def research_import(
        self, notebook_id: str, task_id: str, source_indices: list[int] | None
    ) -> dict:
        self.require("research", "research_import")
        raise NotImplementedError

    # ── Notes (web only) ─────────────────────────────────────────────────────

    async def note_create(
        self, notebook_id: str, content: str, title: str
    ) -> dict:
        self.require("notes", "note_create")
        raise NotImplementedError

    async def note_list(self, notebook_id: str) -> dict:
        self.require("notes", "note_list")
        raise NotImplementedError

    async def note_update(
        self, notebook_id: str, note_id: str, content: str, title: str
    ) -> dict:
        self.require("notes", "note_update")
        raise NotImplementedError

    async def note_delete(self, notebook_id: str, note_id: str) -> dict:
        self.require("notes", "note_delete")
        raise NotImplementedError

    # ── Sharing ──────────────────────────────────────────────────────────────

    async def notebook_share_public(
        self, notebook_id: str, is_public: bool
    ) -> dict:
        self.require("share_public", "notebook_share_public")
        raise NotImplementedError

    async def notebook_share_status(self, notebook_id: str) -> dict:
        self.require("share_public", "notebook_share_status")
        raise NotImplementedError

    # ── Exports / Downloads (web only) ───────────────────────────────────────

    async def export_artifact(
        self, notebook_id: str, artifact_id: str, export_type: str, title: str
    ) -> dict:
        self.require("exports", "export_artifact")
        raise NotImplementedError

    async def download_artifact(
        self,
        notebook_id: str,
        artifact_type: str,
        output_path: str,
        artifact_id: str | None,
    ) -> dict:
        self.require("downloads", "download_artifact")
        raise NotImplementedError

    # ── Podcast (enterprise only) ────────────────────────────────────────────

    async def podcast_create(
        self,
        focus: str,
        length: str,
        contexts: list[dict],
        title: str,
        description: str,
        language_code: str,
    ) -> dict:
        self.require("podcast", "podcast_create")
        raise NotImplementedError

    async def podcast_download(
        self, operation_name: str, output_path: str
    ) -> str:
        self.require("podcast", "podcast_download")
        raise NotImplementedError
