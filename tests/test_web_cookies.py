import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from notebooklm_mcp.auth import cookies
from notebooklm_mcp.auth.cookies import AuthTokens, _coerce_cookies_mapping


class CoerceCookiesMappingTests(unittest.TestCase):
    def test_flat_dict(self) -> None:
        raw = {"SID": "a", "HSID": "b", "SSID": "c", "APISID": "d", "SAPISID": "e"}
        self.assertEqual(_coerce_cookies_mapping(raw), raw)

    def test_playwright_list_overwrites_duplicate_name(self) -> None:
        raw = [
            {"name": "SID", "value": "first", "domain": ".google.com"},
            {"name": "SID", "value": "second", "domain": ".google.com"},
        ]
        self.assertEqual(_coerce_cookies_mapping(raw), {"SID": "second"})

    def test_playwright_list_required_names(self) -> None:
        raw = [
            {"name": "SID", "value": "s", "x": 1},
            {"name": "HSID", "value": "h"},
            {"name": "SSID", "value": "ss"},
            {"name": "APISID", "value": "a"},
            {"name": "SAPISID", "value": "sa"},
        ]
        m = _coerce_cookies_mapping(raw)
        self.assertEqual(
            set(m.keys()),
            {"SID", "HSID", "SSID", "APISID", "SAPISID"},
        )

    def test_rejects_non_collection(self) -> None:
        with self.assertRaises(ValueError):
            _coerce_cookies_mapping("SID=1")


class CookiePersistenceTests(unittest.TestCase):
    def test_save_to_disk_preserves_existing_raw_cookies_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_dir = Path(tmp) / "profiles" / "default"
            profile_dir.mkdir(parents=True)
            raw = [
                {"name": "SID", "value": "s", "domain": ".google.com"},
                {"name": "SID", "value": "s2", "domain": "notebooklm.google.com"},
            ]
            (profile_dir / "cookies.json").write_text(json.dumps(raw), encoding="utf-8")
            (profile_dir / "metadata.json").write_text(
                json.dumps({"email": "user@example.com", "last_validated": "2026-04-23T14:39:10"}),
                encoding="utf-8",
            )

            original_get_settings = cookies.get_settings
            cookies.get_settings = lambda: SimpleNamespace(profile_dir=profile_dir)
            try:
                cookies.save_to_disk(
                    AuthTokens(
                        cookies={"SID": "flattened"},
                        csrf_token="csrf",
                        session_id="sid",
                        build_label="build",
                        extracted_at=123.0,
                    )
                )
            finally:
                cookies.get_settings = original_get_settings

            self.assertEqual(
                json.loads((profile_dir / "cookies.json").read_text(encoding="utf-8")),
                raw,
            )
            metadata = json.loads((profile_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["email"], "user@example.com")
            self.assertEqual(metadata["csrf_token"], "csrf")
