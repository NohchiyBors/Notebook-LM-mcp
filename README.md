# NotebookLM MCP

Dual-mode MCP server for NotebookLM:

- `web` mode works against the NotebookLM web app at `notebooklm.google.com` using an existing browser session and stored cookies.
- `enterprise` mode works against the official NotebookLM Enterprise REST API and standalone Podcast API in Google Cloud.

The active package entrypoint is `notebooklm-mcp`, defined in [pyproject.toml](./pyproject.toml). Runtime mode is selected with `NOTEBOOKLM_MODE=web|enterprise`.

## Modes

| Mode | Backend | Auth | Subscription requirement |
|---|---|---|---|
| `web` | Reverse-engineered `batchexecute` RPC to `notebooklm.google.com` | Google cookies + page tokens | Personal NotebookLM access, including Google AI Pro |
| `enterprise` | Official NotebookLM Enterprise REST API + Podcast API | ADC, Service Account, or `gcloud` token | NotebookLM Enterprise / Gemini Enterprise for notebook APIs |

Notes:

- `web` mode is not an official public Google API. It depends on the current web app behavior.
- `enterprise` mode uses Google Cloud APIs. Notebook APIs and audio overviews require Enterprise access.
- `podcast_create` is a standalone Google Cloud API method and has different licensing rules than notebook APIs.

## What This Server Exposes

Common tools:

- `notebook_create`, `notebook_get`, `notebook_list`, `notebook_delete`
- `notebook_share`
- `source_add_url`, `source_add_urls`, `source_add_text`, `source_add_drive`, `source_add_youtube`, `source_add_batch`
- `source_upload_file`, `source_get`, `source_delete`
- `audio_overview_create`, `audio_overview_delete`
- `refresh_auth`, `server_info`

Web-only tools:

- `notebook_rename`, `notebook_describe`, `notebook_share_public`, `notebook_share_status`
- `source_rename`, `source_sync_drive`, `source_describe`
- `studio_create`, `studio_status`, `studio_delete`, `studio_revise`
- `notebook_query`
- `research_start`, `research_status`, `research_import`
- `note_create`, `note_list`, `note_update`, `note_delete`
- `export_artifact`, `download_artifact`
- `save_auth_tokens`

Enterprise-only tools:

- `podcast_create`
- `podcast_download`

The fuller capability matrix is documented in [docs/architecture.md](./docs/architecture.md).

## Installation

From the repository root:

```bash
uv pip install -e .
```

or:

```bash
pip install -e .
```

Run the server with:

```bash
notebooklm-mcp
```

## MCP Config Example

Web mode:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "notebooklm-mcp",
      "env": {
        "NOTEBOOKLM_MODE": "web",
        "NOTEBOOKLM_PROFILE": "default",
        "NOTEBOOKLM_AUTH_DIR": "~/.notebooklm-mcp-cli"
      }
    }
  }
}
```

Enterprise mode:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "notebooklm-mcp",
      "env": {
        "NOTEBOOKLM_MODE": "enterprise",
        "NOTEBOOKLM_PROJECT_NUMBER": "123456789012",
        "NOTEBOOKLM_PROJECT_ID": "my-project-id",
        "NOTEBOOKLM_LOCATION": "global",
        "NOTEBOOKLM_ENDPOINT_LOCATION": "global"
      }
    }
  }
}
```

## Configuration

Supported environment variables:

- `NOTEBOOKLM_MODE` = `web` or `enterprise`
- `NOTEBOOKLM_PROJECT_NUMBER` for Enterprise notebook APIs
- `NOTEBOOKLM_PROJECT_ID` for Podcast API calls
- `NOTEBOOKLM_LOCATION` = `us`, `eu`, `global`
- `NOTEBOOKLM_ENDPOINT_LOCATION` = `us`, `eu`, `global`
- `NOTEBOOKLM_GOOGLE_APPLICATION_CREDENTIALS` for Service Account auth
- `NOTEBOOKLM_USE_GCLOUD_TOKEN=true` to use `gcloud auth print-access-token`
- `NOTEBOOKLM_PROFILE` for the cookie profile name in `web` mode
- `NOTEBOOKLM_AUTH_DIR` for cookie/profile storage in `web` mode
- `NOTEBOOKLM_LANGUAGE` for the web UI locale parameter
- `NOTEBOOKLM_TIMEOUT`
- `NOTEBOOKLM_MAX_RETRIES`
- `NOTEBOOKLM_LOG_LEVEL` = `DEBUG`, `INFO`, `WARNING`, or `ERROR`
- `NOTEBOOKLM_LOG_FILE` path for persistent logs, default `logs/notebooklm-mcp.log`
- `NOTEBOOKLM_LOG_TO_CONSOLE=true|false`
- `NOTEBOOKLM_LOG_FORMAT=text|json`
- `NOTEBOOKLM_LOG_ARGUMENTS=true|false`, disabled by default to avoid leaking source text
- `NOTEBOOKLM_LOG_MAX_VALUE_LENGTH`

See [.env.example](./.env.example).

## Logging

The server configures package logging at startup and records backend calls, auth refreshes, startup, and shutdown events. Logs go to stderr and `logs/notebooklm-mcp.log` by default.

Examples:

```env
NOTEBOOKLM_LOG_LEVEL=INFO
NOTEBOOKLM_LOG_FILE=logs/notebooklm-mcp.log
NOTEBOOKLM_LOG_FORMAT=json
NOTEBOOKLM_LOG_ARGUMENTS=false
```

By default, call arguments are not logged. If `NOTEBOOKLM_LOG_ARGUMENTS=true`, values are sanitized: cookie/token/session fields are redacted, large text fields are summarized by length, and byte payloads are logged only by size.

## Authentication

Enterprise mode:

- Application Default Credentials
- Service Account JSON via `NOTEBOOKLM_GOOGLE_APPLICATION_CREDENTIALS`
- `gcloud auth print-access-token` via `NOTEBOOKLM_USE_GCLOUD_TOKEN=true`

Useful commands:

```bash
gcloud auth application-default login
gcloud auth login --enable-gdrive-access
```

Web mode:

- Reuse an existing NotebookLM browser session through stored cookies
- Compatible with the `nlm`-style profile layout under `NOTEBOOKLM_AUTH_DIR`
- Use `save_auth_tokens` as a manual fallback if you need to inject cookies directly

## Validation

Local checks:

```bash
python -m compileall src
python -m unittest discover -s tests -v
```

## Docs

- [Architecture and mode matrix](./docs/architecture.md)
- [NotebookLM Enterprise API notes](./docs/notebooklm-enterprise-api.md)
- [Create and manage notebooks (API)](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks)
- [Add and manage data sources in a notebook (API)](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks-sources)
- [Manage audio overview of your notebook (API)](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-audio-overview)
- [Generate podcasts (API method)](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/podcast-api)
