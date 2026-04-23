import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from notebooklm_enterprise_mcp.auth import _get_gcloud_access_token, get_access_token


class AuthTests(unittest.TestCase):
    @patch("notebooklm_enterprise_mcp.auth.subprocess.run")
    def test_get_gcloud_access_token_returns_stdout(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["gcloud", "auth", "print-access-token"],
            returncode=0,
            stdout="token-123\n",
            stderr="",
        )

        self.assertEqual(_get_gcloud_access_token(), "token-123")

    @patch("notebooklm_enterprise_mcp.auth._get_gcloud_access_token")
    @patch("notebooklm_enterprise_mcp.auth.get_settings")
    def test_get_access_token_uses_gcloud_mode(self, mock_get_settings, mock_get_gcloud_access_token) -> None:
        mock_get_settings.return_value = SimpleNamespace(use_gcloud_access_token=True)
        mock_get_gcloud_access_token.return_value = "token-abc"

        self.assertEqual(get_access_token(), "token-abc")
