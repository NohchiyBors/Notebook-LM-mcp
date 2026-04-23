from __future__ import annotations
import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ..config import get_settings

_NOTEBOOKLM_URL = "https://notebooklm.google.com"
_REQUIRED_COOKIES = {"SID", "HSID", "SSID", "APISID", "SAPISID"}

_RE_CSRF    = re.compile(r'"SNlM0e":"([^"]+)"')
_RE_SESSION = re.compile(r'"FdrFJe":"([^"]+)"')
_RE_BUILD   = re.compile(r'"cfb2h":"([^"]+)"')
_BUILD_FALLBACK = "boq_labs-tailwind-frontend_20260108.06_p0"

# CSRF токен живёт долго, но обновляем превентивно каждые 50 минут
_CSRF_MAX_AGE = 50 * 60

# Keepalive: пингуем сервер каждые 25 минут чтобы сессия не умерла
_KEEPALIVE_INTERVAL = 25 * 60


@dataclass
class AuthTokens:
    cookies: dict[str, str] = field(default_factory=dict)
    csrf_token: str = ""
    session_id: str = ""
    build_label: str = _BUILD_FALLBACK
    extracted_at: float = 0.0

    def is_fresh(self, max_age: float = _CSRF_MAX_AGE) -> bool:
        """Возвращает True если токены не старше max_age секунд."""
        if not self.csrf_token:
            return False
        return (time.time() - self.extracted_at) < max_age

    def age_seconds(self) -> float:
        return time.time() - self.extracted_at if self.extracted_at else float("inf")


_tokens: AuthTokens | None = None
_refresh_lock: asyncio.Lock | None = None
_keepalive_task: asyncio.Task | None = None


def _get_lock() -> asyncio.Lock:
    global _refresh_lock
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    return _refresh_lock


# ── Disk I/O ──────────────────────────────────────────────────────────────────

def _profile_dir() -> Path:
    return get_settings().profile_dir


def load_from_disk() -> AuthTokens:
    cookies_path = _profile_dir() / "cookies.json"
    meta_path    = _profile_dir() / "metadata.json"

    if not cookies_path.exists():
        raise FileNotFoundError(
            f"Файл cookies не найден: {cookies_path}\n"
            "Выполните аутентификацию: nlm login  (или save_auth_tokens)"
        )

    cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
    missing = _REQUIRED_COOKIES - set(cookies)
    if missing:
        raise ValueError(f"Отсутствуют обязательные cookies: {missing}")

    meta: dict = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    return AuthTokens(
        cookies=cookies,
        csrf_token=meta.get("csrf_token", ""),
        session_id=meta.get("session_id", ""),
        build_label=meta.get("build_label", _BUILD_FALLBACK),
        extracted_at=meta.get("extracted_at", 0.0),
    )


def save_to_disk(tokens: AuthTokens) -> None:
    profile = _profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    (profile / "cookies.json").write_text(
        json.dumps(tokens.cookies, indent=2), encoding="utf-8"
    )
    (profile / "metadata.json").write_text(
        json.dumps({
            "csrf_token":   tokens.csrf_token,
            "session_id":   tokens.session_id,
            "build_label":  tokens.build_label,
            "extracted_at": tokens.extracted_at,
        }, indent=2),
        encoding="utf-8",
    )


# ── Token extraction ──────────────────────────────────────────────────────────

def _cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def _extract_page_tokens(html: str) -> tuple[str, str, str]:
    csrf    = _RE_CSRF.search(html)
    session = _RE_SESSION.search(html)
    build   = _RE_BUILD.search(html)
    return (
        csrf.group(1)    if csrf    else "",
        session.group(1) if session else "",
        build.group(1)   if build   else _BUILD_FALLBACK,
    )


async def refresh_page_tokens(tokens: AuthTokens) -> AuthTokens:
    """Перезагружает CSRF/session/build токены с homepage NotebookLM."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        resp = await client.get(
            _NOTEBOOKLM_URL,
            headers={"Cookie": _cookie_header(tokens.cookies)},
        )

    location = resp.headers.get("location", "")
    if resp.status_code in (301, 302, 303) and "accounts.google.com" in location:
        raise PermissionError(
            "Cookies просрочены — перенаправление на accounts.google.com. "
            "Выполните повторную аутентификацию: nlm login"
        )

    csrf, session, build = _extract_page_tokens(resp.text)
    if csrf:
        tokens.csrf_token = csrf
    if session:
        tokens.session_id = session
    tokens.build_label = build or tokens.build_label
    tokens.extracted_at = time.time()
    return tokens


# ── Public API ────────────────────────────────────────────────────────────────

def get_tokens() -> AuthTokens:
    global _tokens
    if _tokens is None:
        _tokens = load_from_disk()
    return _tokens


def set_tokens(tokens: AuthTokens) -> None:
    global _tokens
    _tokens = tokens
    save_to_disk(tokens)


def invalidate() -> None:
    global _tokens
    _tokens = None


async def ensure_fresh() -> AuthTokens:
    """
    Гарантирует свежесть токенов.
    Если CSRF старше _CSRF_MAX_AGE — обновляет. Использует lock против гонки.
    """
    tokens = get_tokens()
    if tokens.is_fresh():
        return tokens

    async with _get_lock():
        # Перепроверяем после захвата lock (другой coroutine мог уже обновить)
        tokens = get_tokens()
        if tokens.is_fresh():
            return tokens

        tokens = await refresh_page_tokens(tokens)
        set_tokens(tokens)
        return tokens


# ── Background keepalive ──────────────────────────────────────────────────────

async def _keepalive_loop() -> None:
    """Фоновая задача: пингует NotebookLM каждые 25 минут."""
    while True:
        await asyncio.sleep(_KEEPALIVE_INTERVAL)
        try:
            tokens = get_tokens()
            tokens = await refresh_page_tokens(tokens)
            set_tokens(tokens)
        except Exception:
            # Не прерываем цикл при ошибке — попробуем на следующей итерации
            pass


def start_keepalive() -> None:
    """Запускает фоновый keepalive если ещё не запущен."""
    global _keepalive_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # Нет event loop — keepalive нельзя запустить
    if _keepalive_task is None or _keepalive_task.done():
        _keepalive_task = loop.create_task(_keepalive_loop())


def stop_keepalive() -> None:
    global _keepalive_task
    if _keepalive_task and not _keepalive_task.done():
        _keepalive_task.cancel()
        _keepalive_task = None
