from __future__ import annotations

import functools
import inspect
import json
import logging
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings, get_settings

_LOGGER_NAME = "notebooklm_mcp"
_CONFIG_SIGNATURE: tuple[Any, ...] | None = None

_BASE_RECORD_KEYS = set(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__
)
_BASE_RECORD_KEYS.update({"message", "asctime"})

_SENSITIVE_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "authorization",
    "cookie",
    "csrf",
    "session",
    "sid",
    "key",
)
_LARGE_TEXT_KEYS = (
    "text",
    "texts",
    "content",
    "contents",
    "query",
    "focus",
    "description",
    "cookies_json",
    "data",
    "contexts",
)


class _KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        extras = _record_extras(record)
        if extras:
            line += " " + " ".join(
                f"{key}={json.dumps(value, ensure_ascii=False, default=str)}"
                for key, value in sorted(extras.items())
            )
        return line


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_record_extras(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> logging.Logger:
    """Configure package logging once and return the package logger."""
    global _CONFIG_SIGNATURE

    cfg = settings or get_settings()
    signature = (
        cfg.log_level,
        cfg.log_file,
        cfg.log_to_console,
        cfg.log_format,
        cfg.log_arguments,
        cfg.log_max_value_length,
    )
    logger = logging.getLogger(_LOGGER_NAME)

    if _CONFIG_SIGNATURE == signature and not force:
        return logger

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(_level_number(cfg.log_level))
    logger.propagate = False

    formatter: logging.Formatter
    if cfg.log_format == "json":
        formatter = _JsonFormatter()
    else:
        formatter = _KeyValueFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    if cfg.log_to_console:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        logger.addHandler(console)

    if cfg.log_file_path:
        log_path = cfg.log_file_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    _CONFIG_SIGNATURE = signature
    logger.info(
        "logging_configured",
        extra={
            "event": "logging_configured",
            "log_level": cfg.log_level,
            "log_file": str(cfg.log_file_path) if cfg.log_file_path else None,
            "log_format": cfg.log_format,
            "log_to_console": cfg.log_to_console,
            "log_arguments": cfg.log_arguments,
        },
    )
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    if _CONFIG_SIGNATURE is None:
        configure_logging()
    if not name:
        return logging.getLogger(_LOGGER_NAME)
    return logging.getLogger(f"{_LOGGER_NAME}.{name}")


class LoggedBackend:
    """Proxy that logs backend method calls without changing backend behavior."""

    def __init__(self, backend: Any, *, mode: str) -> None:
        self._backend = backend
        self._mode = mode
        self._logger = get_logger("backend")

    def supports(self, feature: str) -> bool:
        return self._backend.supports(feature)

    def require(self, feature: str, tool_name: str) -> None:
        try:
            return self._backend.require(feature, tool_name)
        except Exception:
            self._logger.warning(
                "backend_feature_unavailable",
                extra={
                    "event": "backend_feature_unavailable",
                    "mode": self._mode,
                    "feature": feature,
                    "tool": tool_name,
                },
            )
            raise

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._backend, name)
        if name.startswith("_") or not callable(target):
            return target
        if not inspect.iscoroutinefunction(target):
            return target

        @functools.wraps(target)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cfg = get_settings()
            call_id = uuid.uuid4().hex[:12]
            started_at = time.perf_counter()
            extra: dict[str, Any] = {
                "event": "backend_call_start",
                "call_id": call_id,
                "mode": self._mode,
                "backend": self._backend.__class__.__name__,
                "operation": name,
            }
            if cfg.log_arguments:
                extra["arguments"] = summarize_call_arguments(args, kwargs, cfg)
            else:
                extra["arg_count"] = len(args)
                extra["kwarg_names"] = sorted(kwargs.keys())

            self._logger.info("backend_call_start", extra=extra)

            try:
                result = await target(*args, **kwargs)
            except Exception as exc:
                self._logger.exception(
                    "backend_call_error",
                    extra={
                        "event": "backend_call_error",
                        "call_id": call_id,
                        "mode": self._mode,
                        "backend": self._backend.__class__.__name__,
                        "operation": name,
                        "duration_ms": _duration_ms(started_at),
                        "error_type": exc.__class__.__name__,
                    },
                )
                raise

            self._logger.info(
                "backend_call_success",
                extra={
                    "event": "backend_call_success",
                    "call_id": call_id,
                    "mode": self._mode,
                    "backend": self._backend.__class__.__name__,
                    "operation": name,
                    "duration_ms": _duration_ms(started_at),
                    "result": summarize_value(result, cfg),
                },
            )
            return result

        return wrapper


def summarize_call_arguments(args: tuple[Any, ...], kwargs: dict[str, Any], cfg: Settings) -> dict:
    return {
        "args": [summarize_value(value, cfg) for value in args],
        "kwargs": {
            key: summarize_value(value, cfg, key=key)
            for key, value in sorted(kwargs.items())
        },
    }


def summarize_value(value: Any, cfg: Settings | None = None, *, key: str = "") -> Any:
    cfg = cfg or get_settings()
    lowered_key = key.lower()
    if lowered_key and any(part in lowered_key for part in _SENSITIVE_KEY_PARTS):
        return "<redacted>"

    if value is None or isinstance(value, bool | int | float):
        return value

    if isinstance(value, str):
        if lowered_key and any(part in lowered_key for part in _LARGE_TEXT_KEYS):
            return _text_summary(value)
        return _truncate(value, cfg.log_max_value_length)

    if isinstance(value, bytes | bytearray):
        return {"type": "bytes", "length": len(value)}

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(item_key): summarize_value(item_value, cfg, key=str(item_key))
            for item_key, item_value in list(value.items())[:20]
        } | ({"<truncated>": len(value)} if len(value) > 20 else {})

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        values = list(value)
        return {
            "type": "list",
            "length": len(values),
            "items": [summarize_value(item, cfg) for item in values[:5]],
            **({"truncated": True} if len(values) > 5 else {}),
        }

    return _truncate(repr(value), cfg.log_max_value_length)


def _record_extras(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _BASE_RECORD_KEYS and not key.startswith("_")
    }


def _level_number(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def _duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 3)] + "..."


def _text_summary(text: str) -> dict[str, Any]:
    return {"type": "text", "length": len(text)}
