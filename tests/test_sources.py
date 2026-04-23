import unittest

from notebooklm_enterprise_mcp.models import SourceBatchItem
from notebooklm_enterprise_mcp.tools.sources import _build_user_content


class SourcePayloadTests(unittest.TestCase):
    def test_drive_source_payload_uses_supported_google_mime_type(self) -> None:
        payload = _build_user_content(
            SourceBatchItem(
                kind="drive",
                document_id="doc-123",
                doc_type="slide",
                display_name="Deck",
            )
        )

        self.assertEqual(
            payload,
            {
                "googleDriveContent": {
                    "documentId": "doc-123",
                    "mimeType": "application/vnd.google-apps.presentation",
                    "sourceName": "Deck",
                }
            },
        )

    def test_text_source_requires_text(self) -> None:
        with self.assertRaises(ValueError):
            SourceBatchItem(kind="text")
