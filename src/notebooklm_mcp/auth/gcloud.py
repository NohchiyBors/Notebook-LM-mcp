from __future__ import annotations
import subprocess

import google.auth
import google.auth.transport.requests
import google.oauth2.service_account
from google.auth.credentials import Credentials

from ..config import get_settings

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_credentials: Credentials | None = None


def _load_credentials() -> Credentials:
    cfg = get_settings()
    if cfg.google_application_credentials:
        return google.oauth2.service_account.Credentials.from_service_account_file(
            cfg.google_application_credentials, scopes=_SCOPES
        )
    creds, _ = google.auth.default(scopes=_SCOPES)
    return creds


def _gcloud_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "gcloud auth print-access-token завершился с ошибкой"
            + (f": {result.stderr.strip()}" if result.stderr.strip() else "")
        )
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("gcloud auth print-access-token вернул пустой токен")
    return token


def get_access_token() -> str:
    cfg = get_settings()
    if cfg.use_gcloud_token:
        return _gcloud_token()

    global _credentials
    if _credentials is None:
        _credentials = _load_credentials()

    request = google.auth.transport.requests.Request()
    if not _credentials.valid:
        _credentials.refresh(request)

    return _credentials.token
