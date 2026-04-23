"""Парсинг ответов batchexecute и batchexecute-streaming."""
from __future__ import annotations
import json
import re


_ANTI_XSSI = b")]}'\n"


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
    if body.startswith(_ANTI_XSSI):
        body = body[len(_ANTI_XSSI):]

    text = body.decode("utf-8", errors="replace")
    chunks = _split_chunks(text)

    for chunk in chunks:
        try:
            items = json.loads(chunk)
        except (json.JSONDecodeError, ValueError):
            continue

        result = _find_rpc_result(items, rpc_id)
        if result is not None:
            return result

    raise ValueError(f"RPC результат для '{rpc_id}' не найден в ответе")


def _split_chunks(text: str) -> list[str]:
    """Разбивает ответ на JSON-чанки по маркерам размера."""
    chunks: list[str] = []
    i = 0
    while i < len(text):
        # Найти число (размер чанка)
        m = re.search(r"\d+", text[i:])
        if not m:
            break
        size_start = i + m.start()
        size_end = i + m.end()
        size = int(m.group())

        # После числа должен идти \n
        if size_end < len(text) and text[size_end] == "\n":
            chunk_start = size_end + 1
            chunk = text[chunk_start: chunk_start + size]
            chunks.append(chunk)
            i = chunk_start + size
        else:
            i = size_end
    return chunks


def _find_rpc_result(items: list, rpc_id: str) -> list | None:
    """Рекурсивно ищет ["wrb.fr", rpc_id, result_str] в списке."""
    for item in items:
        if not isinstance(item, list):
            continue
        if len(item) >= 3 and item[0] == "wrb.fr" and item[1] == rpc_id:
            raw = item[2]
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
    text = body.decode("utf-8", errors="replace")
    if text.startswith(")]}'\n"):
        text = text[5:]

    best: str = ""
    for chunk in _split_chunks(text):
        try:
            items = json.loads(chunk)
        except (json.JSONDecodeError, ValueError):
            continue
        result = _find_rpc_result(items, rpc_id)
        if result and isinstance(result, list):
            # Текст ответа обычно на позиции [0][0] или [1][0][0][1]
            candidate = safe_get(result, 0, 0, default="")
            if isinstance(candidate, str) and len(candidate) > len(best):
                best = candidate
    return best
