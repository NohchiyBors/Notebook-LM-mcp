import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from notebooklm_mcp.config import Settings
from notebooklm_mcp.observability import (
    LoggedBackend,
    configure_logging,
    summarize_value,
)


class DummyBackend:
    def supports(self, feature: str) -> bool:
        return feature == "dummy"

    def require(self, feature: str, tool_name: str) -> None:
        if not self.supports(feature):
            raise NotImplementedError(tool_name)

    async def notebook_list(self, page_size: int = 100) -> dict:
        return {"items": [1, 2], "page_size": page_size}


class ObservabilityTests(unittest.TestCase):
    @patch.dict(os.environ, {k: v for k, v in os.environ.items() if not k.startswith("NOTEBOOKLM_")}, clear=True)
    def test_logging_settings_defaults(self) -> None:
        # Без .env в cwd pydantic-settings не подставляет локальный NOTEBOOKLM_* из файла репозитория.
        with tempfile.TemporaryDirectory() as tmp:
            prev = os.getcwd()
            os.chdir(tmp)
            try:
                settings = Settings()
            finally:
                os.chdir(prev)

        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.log_file, "logs/notebooklm-mcp.log")
        self.assertTrue(settings.log_to_console)
        self.assertEqual(settings.log_format, "text")
        self.assertFalse(settings.log_arguments)

    def test_log_file_empty_string_disables_file_logging(self) -> None:
        settings = Settings(log_file="")

        self.assertIsNone(settings.log_file)
        self.assertIsNone(settings.log_file_path)

    def test_summarize_value_redacts_sensitive_values(self) -> None:
        settings = Settings()

        self.assertEqual(summarize_value("secret", settings, key="csrf_token"), "<redacted>")
        self.assertEqual(summarize_value("token", settings, key="authorization"), "<redacted>")

    def test_summarize_value_summarizes_large_text_fields(self) -> None:
        settings = Settings()

        self.assertEqual(
            summarize_value("hello world", settings, key="query"),
            {"type": "text", "length": 11},
        )

    def test_logged_backend_writes_call_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "server.log"
            settings = Settings(
                log_file=str(log_file),
                log_to_console=False,
                log_arguments=True,
            )
            configure_logging(settings, force=True)

            try:
                backend = LoggedBackend(DummyBackend(), mode="web")
                result = asyncio.run(backend.notebook_list(page_size=7))

                self.assertEqual(result["page_size"], 7)
                content = log_file.read_text(encoding="utf-8")
                self.assertIn("backend_call_start", content)
                self.assertIn("backend_call_success", content)
            finally:
                configure_logging(Settings(log_file=None, log_to_console=False), force=True)
