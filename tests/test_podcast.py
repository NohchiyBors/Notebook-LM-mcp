import tempfile
import unittest
from pathlib import Path

from notebooklm_enterprise_mcp.models import PodcastContextInput
from notebooklm_enterprise_mcp.tools.podcast import (
    _build_contexts_from_inputs,
    _build_podcast_body,
)


class PodcastBodyTests(unittest.TestCase):
    def test_build_podcast_body_omits_empty_language_code(self) -> None:
        body = _build_podcast_body(
            focus="Summarize this",
            contexts=[{"text": "hello"}],
            length="SHORT",
            title="Demo",
            description="Desc",
            language_code="",
        )

        self.assertEqual(body["podcastConfig"]["focus"], "Summarize this")
        self.assertEqual(body["podcastConfig"]["length"], "SHORT")
        self.assertNotIn("languageCode", body["podcastConfig"])
        self.assertEqual(body["title"], "Demo")
        self.assertEqual(body["description"], "Desc")


class PodcastContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_contexts_from_inputs_preserves_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.mp3"
            audio_path.write_bytes(b"fake-audio")

            payloads = await _build_contexts_from_inputs(
                [
                    PodcastContextInput(kind="text", text="first"),
                    PodcastContextInput(kind="file", file_path=str(audio_path)),
                ]
            )

        self.assertEqual(payloads[0], {"text": "first"})
        self.assertIn("inlineData", payloads[1])
        self.assertEqual(payloads[1]["inlineData"]["mimeType"], "audio/mpeg")
        self.assertTrue(payloads[1]["inlineData"]["data"])
