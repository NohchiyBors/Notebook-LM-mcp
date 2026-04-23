"""Парсинг ответов batchexecute и batchexecute-streaming."""
from __future__ import annotations
import json
from typing import Any


_ANTI_XSSI = b")]}'\n"


class NotebookLMRpcError(ValueError):
    """Structured batchexecute RPC error."""

    def __init__(self, message: str, *, rpc_id: str, code: object = None) -> None:
        super().__init__(message)
        self.rpc_id = rpc_id
        self.code = code

    @property
    def is_auth_error(self) -> bool:
        return isinstance(self.code, list) and 16 in self.code


def _decode_batchexecute_text(body: bytes) -> str:
    """Снимает anti-XSSI-префикс и ведущие переводы строк."""
    text = body.decode("utf-8", errors="replace")
    if text.startswith(")]}'"):
        text = text[4:]
    while text and text[0] in "\r\n":
        text = text[1:]
    return text


def _iter_batchexecute_json_roots(text: str) -> list[Any]:
    """
    Разбирает тело batchexecute построчно.

    Сервер шлёт пары строк «размер» (число) + JSON; число — ориентир, реальный
    JSON всегда на следующей строке. Срез по длине в символах ломает разбор,
    если длина в байтах не совпадает с длиной одной строки JSON.
    """
    lines = text.split("\n")
    roots: list[Any] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        try:
            int(line)
        except ValueError:
            try:
                roots.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                pass
            i += 1
            continue
        i += 1
        if i >= len(lines):
            break
        try:
            roots.append(json.loads(lines[i]))
        except (json.JSONDecodeError, ValueError):
            pass
        i += 1
    return roots


def parse_batchexecute(body: bytes, rpc_id: str) -> list:
    """
    Извлекает результат RPC из ответа batchexecute.

    Формат ответа:
        )]}'\n
        {N}\n
        [["wrb.fr","{rpc_id}","{result_json}",...],...]
        \n
        {N}\n
        ...
    """
    text = _decode_batchexecute_text(body)
    for items in _iter_batchexecute_json_roots(text):
        if not isinstance(items, list):
            continue
        result = _find_rpc_result(items, rpc_id)
        if result is not None:
            return result

    raise ValueError(f"RPC результат для '{rpc_id}' не найден в ответе")


def _find_rpc_result(items: list, rpc_id: str) -> list | None:
    """Рекурсивно ищет ["wrb.fr", rpc_id, result_str] в списке."""
    for item in items:
        if not isinstance(item, list):
            continue
        if len(item) >= 3 and item[0] == "wrb.fr" and item[1] == rpc_id:
            raw = item[2]
            if raw is None:
                code = item[5] if len(item) > 5 else None
                hint = (
                    f"NotebookLM вернул пустой результат для RPC «{rpc_id}»"
                    + (f" (код {code})" if code is not None else "")
                    + ". Обычно это сессия или доступ: выполните nlm login "
                    "или войдите в NotebookLM в браузере с тем же аккаунтом и обновите cookies."
                )
                raise NotebookLMRpcError(hint, rpc_id=rpc_id, code=code)
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    return []
            return raw
        # Рекурсивный поиск во вложенных списках
        found = _find_rpc_result(item, rpc_id)
        if found is not None:
            return found
    return None


def safe_get(data: list, *indices: int, default=None):
    """Безопасное обращение по цепочке индексов к вложенным спискам."""
    current = data
    for idx in indices:
        if not isinstance(current, (list, tuple)) or idx >= len(current):
            return default
        current = current[idx]
    return current


def parse_streaming_query(body: bytes, rpc_id: str) -> str:
    """Извлекает текстовый ответ из streaming query."""
    text = _decode_batchexecute_text(body)

    best: str = ""
    for items in _iter_batchexecute_json_roots(text):
        if not isinstance(items, list):
            continue
        result = _find_rpc_result(items, rpc_id)
        if result and isinstance(result, list):
            # Текст ответа обычно на позиции [0][0] или [1][0][0][1]
            candidate = safe_get(result, 0, 0, default="")
            if isinstance(candidate, str) and len(candidate) > len(best):
                best = candidate
    return best
