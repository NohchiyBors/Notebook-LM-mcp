import google.auth
import google.auth.transport.requests
import google.oauth2.service_account
import subprocess
from google.auth.credentials import Credentials

from .config import get_settings

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

_credentials: Credentials | None = None


def _load_credentials() -> Credentials:
    settings = get_settings()

    if settings.google_application_credentials:
        creds = google.oauth2.service_account.Credentials.from_service_account_file(
            settings.google_application_credentials,
            scopes=_SCOPES,
        )
    else:
        creds, _ = google.auth.default(scopes=_SCOPES)

    return creds


def _get_gcloud_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            "Failed to get access token via gcloud auth print-access-token"
            + (f": {stderr}" if stderr else "")
        )

    token = result.stdout.strip()
    if not token:
        raise RuntimeError("gcloud auth print-access-token returned an empty token.")

    return token


def get_access_token() -> str:
    settings = get_settings()
    if settings.use_gcloud_access_token:
        return _get_gcloud_access_token()

    global _credentials

    if _credentials is None:
        _credentials = _load_credentials()

    request = google.auth.transport.requests.Request()
    if not _credentials.valid:
        _credentials.refresh(request)

    return _credentials.token
