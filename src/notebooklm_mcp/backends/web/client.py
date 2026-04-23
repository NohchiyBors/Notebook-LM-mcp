"""HTTP-клиент для batchexecute RPC к notebooklm.google.com."""
from __future__ import annotations
import asyncio
import json
from urllib.parse import quote

import httpx

from ...config import get_settings
from ...auth import cookies as cookie_store
from .parsers import parse_batchexecute, parse_streaming_query

_BASE = "https://notebooklm.google.com"
_BATCHEXECUTE = f"{_BASE}/_/LabsTailwindUi/data/batchexecute"
_QUERY_ENDPOINT = (
    f"{_BASE}/_/LabsTailwindUi/data/"
    "google.internal.labs.tailwind.orchestration.v1."
    "LabsTailwindOrchestrationService/GenerateFreeFormStreamed"
)
_UPLOAD_INIT = f"{_BASE}/upload/_/?authuser=0"

_RETRYABLE = {429, 500, 502, 503, 504}
_reqid_counter = 100000


def _next_reqid() -> int:
    global _reqid_counter
    _reqid_counter += 100000
    return _reqid_counter


class WebClient:
    def __init__(self) -> None:
        cfg = get_settings()
        self._timeout = cfg.timeout
        self._max_retries = cfg.max_retries
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout, connect=10),
            follow_redirects=False,
        )

    # ── Вспомогательные методы ───────────────────────────────────────────────

    def _base_headers(self, tokens: cookie_store.AuthTokens) -> dict[str, str]:
        return {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": _BASE,
            "Referer": _BASE + "/",
            "X-Same-Domain": "1",
            "X-Goog-Csrf-Token": tokens.csrf_token,
            "Cookie": "; ".join(f"{k}={v}" for k, v in tokens.cookies.items()),
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }

    def _build_body(self, rpc_id: str, params: list, csrf_token: str) -> bytes:
        params_json = json.dumps(params, separators=(",", ":"), ensure_ascii=False)
        f_req = json.dumps(
            [[[rpc_id, params_json, None, "generic"]]],
            separators=(",", ":"),
        )
        encoded_req = quote(f_req, safe="")
        encoded_csrf = quote(csrf_token, safe="")
        return f"f.req={encoded_req}&at={encoded_csrf}&".encode()

    def _batchexecute_url(
        self,
        rpc_id: str,
        tokens: cookie_store.AuthTokens,
        source_path: str = "/",
    ) -> str:
        params = (
            f"rpcids={rpc_id}"
            f"&source-path={quote(source_path)}"
            f"&bl={quote(tokens.build_label)}"
            f"&hl={get_settings().language}"
            f"&rt=c"
        )
        if tokens.session_id:
            params += f"&f.sid={quote(tokens.session_id)}"
        return f"{_BATCHEXECUTE}?{params}"

    # ── Основной вызов RPC ───────────────────────────────────────────────────

    async def call(
        self,
        rpc_id: str,
        params: list,
        source_path: str = "/",
    ) -> list:
        # Проактивно обновляем токены если устарели (> 50 мин)
        tokens = await cookie_store.ensure_fresh()

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post(
                    self._batchexecute_url(rpc_id, tokens, source_path),
                    headers=self._base_headers(tokens),
                    content=self._build_body(rpc_id, params, tokens.csrf_token),
                )
            except httpx.TimeoutException as e:
                raise TimeoutError(f"Таймаут запроса RPC {rpc_id}") from e

            if resp.status_code in (401, 403) or _is_auth_error(resp):
                tokens = await self._refresh_auth(tokens)
                continue

            if resp.status_code in _RETRYABLE:
                if attempt < self._max_retries:
                    await asyncio.sleep(min(2 ** attempt, 16))
                    continue
                resp.raise_for_status()

            resp.raise_for_status()
            return parse_batchexecute(resp.content, rpc_id)

        raise RuntimeError(f"RPC {rpc_id} завершился ошибкой после {self._max_retries} попыток")

    async def _refresh_auth(self, tokens: cookie_store.AuthTokens) -> cookie_store.AuthTokens:
        """Обновляет CSRF/session токены реактивно (при 401/403)."""
        try:
            tokens = await cookie_store.refresh_page_tokens(tokens)
            cookie_store.set_tokens(tokens)
        except PermissionError:
            # Cookies полностью протухли — перезагрузить с диска и попробовать снова
            cookie_store.invalidate()
            tokens = cookie_store.load_from_disk()
            tokens = await cookie_store.refresh_page_tokens(tokens)
            cookie_store.set_tokens(tokens)
        return tokens

    # ── Streaming query ──────────────────────────────────────────────────────

    async def query(
        self,
        params: list,
        rpc_id: str = "streamQuery",
    ) -> str:
        tokens = await cookie_store.ensure_fresh()

        reqid = _next_reqid()
        url = (
            f"{_QUERY_ENDPOINT}"
            f"?bl={quote(tokens.build_label)}"
            f"&hl={get_settings().language}"
            f"&_reqid={reqid}"
            f"&rt=c"
        )
        if tokens.session_id:
            url += f"&f.sid={quote(tokens.session_id)}"

        body = self._build_body(rpc_id, params, tokens.csrf_token)
        resp = await self._http.post(url, headers=self._base_headers(tokens), content=body)
        resp.raise_for_status()
        return parse_streaming_query(resp.content, rpc_id)

    # ── File upload (resumable, 3-step) ──────────────────────────────────────

    async def upload_file(
        self,
        notebook_id: str,
        source_id: str,
        filename: str,
        data: bytes,
        mime_type: str,
    ) -> None:
        tokens = cookie_store.get_tokens()
        headers_base = {
            "Cookie": "; ".join(f"{k}={v}" for k, v in tokens.cookies.items()),
            "Origin": _BASE,
        }

        # Step 2: Начать сессию загрузки
        init_body = json.dumps({
            "PROJECT_ID": notebook_id,
            "SOURCE_NAME": filename,
            "SOURCE_ID": source_id,
        }).encode()

        init_resp = await self._http.post(
            _UPLOAD_INIT,
            headers={
                **headers_base,
                "Content-Type": "application/json",
                "x-goog-upload-protocol": "resumable",
                "x-goog-upload-command": "start",
                "x-goog-upload-header-content-length": str(len(data)),
                "x-goog-upload-header-content-type": mime_type,
            },
            content=init_body,
        )
        init_resp.raise_for_status()

        upload_url = init_resp.headers.get("x-goog-upload-url")
        if not upload_url:
            raise RuntimeError("Не получен x-goog-upload-url от сервера")

        # Step 3: Загрузить файл
        upload_resp = await self._http.post(
            upload_url,
            headers={
                **headers_base,
                "Content-Type": mime_type,
                "x-goog-upload-protocol": "resumable",
                "x-goog-upload-command": "upload, finalize",
                "x-goog-upload-offset": "0",
            },
            content=data,
        )
        upload_resp.raise_for_status()

    async def aclose(self) -> None:
        await self._http.aclose()


def _is_auth_error(resp: httpx.Response) -> bool:
    """Проверяет наличие RPC Error 16 (auth) в теле ответа."""
    try:
        text = resp.text[:1000]
        return '"error":16' in text or '"Error":16' in text
    except Exception:
        return False


_client: WebClient | None = None


def get_web_client() -> WebClient:
    global _client
    if _client is None:
        _client = WebClient()
    return _client
