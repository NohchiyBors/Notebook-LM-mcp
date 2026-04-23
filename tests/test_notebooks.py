import unittest

from notebooklm_enterprise_mcp.models import NotebookShareGrant
from notebooklm_enterprise_mcp.tools.notebooks import _share_body


class NotebookShareTests(unittest.TestCase):
    def test_share_body_supports_multiple_grants(self) -> None:
        body = _share_body(
            [
                NotebookShareGrant(email="reader@example.com", role="PROJECT_ROLE_READER"),
                NotebookShareGrant(email="writer@example.com", role="PROJECT_ROLE_WRITER"),
            ]
        )

        self.assertEqual(
            body,
            {
                "accountAndRoles": [
                    {"email": "reader@example.com", "role": "PROJECT_ROLE_READER"},
                    {"email": "writer@example.com", "role": "PROJECT_ROLE_WRITER"},
                ]
            },
        )

    def test_share_body_rejects_empty_grants(self) -> None:
        with self.assertRaises(ValueError):
            _share_body([])
