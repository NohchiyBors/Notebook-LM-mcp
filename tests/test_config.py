import unittest

from notebooklm_enterprise_mcp.config import Settings


class SettingsTests(unittest.TestCase):
    def test_source_upload_url_uses_upload_endpoint(self) -> None:
        settings = Settings(
            project_number="123456789012",
            project_id="my-project-id",
            location="global",
            endpoint_location="us",
        )

        self.assertEqual(
            settings.source_upload_url("nb-123"),
            (
                "https://us-discoveryengine.googleapis.com/upload/v1alpha/"
                "projects/123456789012/locations/global/notebooks/nb-123/sources:uploadFile"
            ),
        )

    def test_podcasts_url_prefers_project_id(self) -> None:
        settings = Settings(
            project_number="123456789012",
            project_id="my-project-id",
            location="global",
            endpoint_location="global",
        )

        self.assertEqual(
            settings.podcasts_url,
            "https://discoveryengine.googleapis.com/v1/projects/my-project-id/locations/global/podcasts",
        )

    def test_podcasts_url_falls_back_to_project_number(self) -> None:
        settings = Settings(
            project_number="123456789012",
            location="global",
            endpoint_location="global",
        )

        self.assertEqual(
            settings.podcasts_url,
            "https://discoveryengine.googleapis.com/v1/projects/123456789012/locations/global/podcasts",
        )
