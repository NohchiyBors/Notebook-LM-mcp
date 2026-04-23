# Архитектура: NotebookLM Dual-Mode MCP Server

## Концепция

Единый MCP-сервер с двумя режимами работы, выбираемыми через конфигурацию:

| Режим | Backend | Аутентификация | Доступность |
|---|---|---|---|
| **enterprise** | NotebookLM Enterprise REST API (`discoveryengine.googleapis.com/v1alpha`) | Google Cloud ADC / Service Account | Только с подпиской Enterprise |
| **web** | Reverse-engineered `notebooklm.google.com` batchexecute RPC | Google cookies (браузерная сессия) | Бесплатно (личный аккаунт) |

Инструменты — единые для обоих режимов. Режим влияет только на внутреннюю реализацию backend-адаптера.

---

## Доступность инструментов по режимам

| Инструмент | Enterprise | Web |
|---|:---:|:---:|
| notebook_create / get / list / delete | ✅ | ✅ |
| notebook_share / share_batch | ✅ | ✅ |
| source_add_url / text / drive / youtube | ✅ | ✅ |
| source_upload_file | ✅ | ✅ |
| source_get / delete | ✅ | ✅ |
| source_rename | ❌ | ✅ |
| source_sync_drive | ❌ | ✅ |
| notebook_query (chat) | ❌ | ✅ |
| research_start / status / import | ❌ | ✅ |
| audio_overview_create / delete | ✅ | ✅ |
| studio_create (video/slides/report/quiz/...) | ❌ | ✅ |
| studio_status / delete / revise | ❌ | ✅ |
| note_create / list / update / delete | ❌ | ✅ |
| export_artifact (Docs/Sheets) | ❌ | ✅ |
| download_artifact | ❌ | ✅ |
| notebook_describe | ❌ | ✅ |
| podcast_create / download | ✅ | ❌ |

> Enterprise API в Preview (v1alpha) — набор инструментов может расширяться.

---

## Структура проекта

```
src/notebooklm_mcp/
├── __init__.py
├── server.py                  # FastMCP + регистрация инструментов
├── config.py                  # Pydantic-settings, определение режима
│
├── backends/
│   ├── __init__.py
│   ├── base.py                # Абстрактный Backend (протокол/ABC)
│   ├── enterprise.py          # Enterprise REST API backend
│   └── web/
│       ├── __init__.py
│       ├── client.py          # HTTP-клиент (batchexecute RPC)
│       ├── auth.py            # Cookie auth, CSRF, session tokens
│       ├── rpc.py             # RPC ID константы и вызов
│       ├── parsers.py         # Парсинг ответов batchexecute
│       └── upload.py          # Resumable upload (3-step)
│
├── auth/
│   ├── __init__.py
│   ├── gcloud.py              # ADC / Service Account токены
│   └── cookies.py             # Cookie store (файлы, профили)
│
├── models/
│   ├── __init__.py
│   └── common.py              # Pydantic-модели ответов (общие)
│
└── tools/
    ├── __init__.py
    ├── notebooks.py           # create/get/list/delete/share
    ├── sources.py             # add/upload/get/delete/rename/sync
    ├── audio.py               # audio_overview_create/delete
    ├── podcast.py             # podcast_create/download (enterprise only)
    ├── studio.py              # studio_create/status/delete/revise (web only)
    ├── query.py               # notebook_query (web only)
    ├── research.py            # research_start/status/import (web only)
    ├── notes.py               # note CRUD (web only)
    ├── sharing.py             # share_public/invite/status
    └── exports.py             # export_artifact (web only)
```

---

## Backend-абстракция

Каждый инструмент получает backend через DI и вызывает методы абстрактного интерфейса:

```python
# backends/base.py
from abc import ABC, abstractmethod

class NotebookLMBackend(ABC):

    @abstractmethod
    async def notebook_create(self, title: str) -> dict: ...

    @abstractmethod
    async def notebook_get(self, notebook_id: str) -> dict: ...

    @abstractmethod
    async def notebook_list(self, page_size: int) -> dict: ...

    @abstractmethod
    async def notebook_delete(self, notebook_ids: list[str]) -> dict: ...

    @abstractmethod
    async def source_add_url(self, notebook_id: str, url: str, display_name: str) -> dict: ...

    # ... остальные методы

    def supports(self, feature: str) -> bool:
        """Возвращает True если данный режим поддерживает фичу."""
        return feature in self._supported_features
```

Инструменты, недоступные в текущем режиме, возвращают понятную ошибку:

```python
@mcp.tool()
async def studio_create(...) -> dict:
    backend = get_backend()
    if not backend.supports("studio"):
        return {
            "error": "studio_create недоступен в Enterprise режиме. "
                     "Переключитесь на режим 'web' для доступа к Studio."
        }
    return await backend.studio_create(...)
```

---

## Аутентификация

### Enterprise режим (Google Cloud)

```
Приоритет:
1. NOTEBOOKLM_GOOGLE_APPLICATION_CREDENTIALS → Service Account JSON
2. NOTEBOOKLM_USE_GCLOUD_TOKEN=true → gcloud auth print-access-token
3. Application Default Credentials (ADC) → gcloud auth application-default login
```

**Для Drive источников** требует отдельных user credentials:
```bash
gcloud auth login --enable-gdrive-access
```

### Web режим (Cookie-based)

```
Хранилище: ~/.notebooklm-mcp/profiles/{profile}/
  cookies.json     — Google auth cookies
  metadata.json    — CSRF token, session_id, build_label, email, last_validated

Требуемые cookies: SID, HSID, SSID, APISID, SAPISID
```

**Получение куков:**
- Через `nlm login` (если установлен `notebooklm-mcp-cli`)
- Через Chrome DevTools Protocol (CDP) — автоматически из браузера
- Через `save_auth_tokens` MCP-инструмент (ручной ввод)

**CSRF и Session tokens** извлекаются автоматически из HTML страницы при первом запросе.

**Авто-обновление** при 401/403:
1. Перезагрузить CSRF/session из homepage
2. Перезагрузить cookies с диска
3. Запустить headless auth (если есть Chrome профиль)

---

## Web режим: RPC-протокол

Все запросы к `notebooklm.google.com` используют протокол `batchexecute`:

```
POST /_/LabsTailwindUi/data/batchexecute
  ?rpcids={RPC_ID}
  &source-path={PATH}
  &bl={BUILD_LABEL}
  &hl=en
  &rt=c
  &f.sid={SESSION_ID}

Body (application/x-www-form-urlencoded):
  f.req=[[["{RPC_ID}","{PARAMS_JSON}",null,"generic"]]]&at={CSRF_TOKEN}&

Headers:
  Content-Type: application/x-www-form-urlencoded;charset=UTF-8
  X-Same-Domain: 1
  X-Goog-Csrf-Token: {CSRF_TOKEN}
  Origin: https://notebooklm.google.com
  Referer: https://notebooklm.google.com/
```

**Ответ:**
```
)]}'\n
{BYTE_COUNT}\n
[["wrb.fr","{RPC_ID}","{RESULT_JSON}",...],...]\n
```

Парсинг: убрать `)]}'\n`, разобрать чанки по размеру, найти `"wrb.fr"` с нужным RPC_ID, JSON-распарсить поле [2].

### Ключевые RPC ID

| RPC ID | Операция |
|---|---|
| `CCqFvf` | notebook_create |
| `wXbhsf` | notebook_list |
| `rLM1Ne` | notebook_get |
| `WWINqb` | notebook_delete |
| `s0tc2d` | notebook_rename |
| `izAoDd` | source_add (url/text/drive) |
| `o4cbdc` | source_file_register |
| `hizoJc` | source_get |
| `tGMBJ` | source_delete |
| `b7Wfje` | source_rename |
| `FLmJqe` | source_sync_drive |
| `R7cb6c` | studio_create |
| `gArtLc` | studio_poll |
| `V5N4be` | studio_delete |
| `KmcKPe` | studio_revise_slides |
| `Ljjv0c` | research_fast |
| `QA9ei` | research_deep |
| `e3bVqc` | research_poll |
| `LBwxtb` | research_import |
| `QDyure` | notebook_share |
| `JFMDGd` | share_status |
| `Krh3pd` | export_artifact |
| `CYK0Xb` | note_create |
| `cFji9` | note_list |
| `cYAfTb` | note_update |
| `AH0mwd` | note_delete |
| `VfAZjd` | notebook_describe |
| `tr032e` | source_describe |

**Query (streaming):**
```
POST /_/LabsTailwindUi/data/
  google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/
  GenerateFreeFormStreamed
```

### Resumable File Upload (web режим)

```
1. POST batchexecute (RPC o4cbdc) → SOURCE_ID
2. POST /upload/_/?authuser=0
   Headers: x-goog-upload-protocol: resumable, x-goog-upload-command: start
   Body: {"PROJECT_ID": notebook_id, "SOURCE_NAME": filename, "SOURCE_ID": source_id}
   Response header: x-goog-upload-url

3. POST {upload_url}
   Headers: x-goog-upload-command: upload, finalize
   Body: raw file bytes (64KB chunks)
```

---

## Конфигурация

```env
# Режим работы (обязательно)
NOTEBOOKLM_MODE=web          # web | enterprise

# Enterprise режим
NOTEBOOKLM_PROJECT_NUMBER=123456789012
NOTEBOOKLM_PROJECT_ID=my-project-id
NOTEBOOKLM_LOCATION=global
NOTEBOOKLM_ENDPOINT_LOCATION=global
NOTEBOOKLM_GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
NOTEBOOKLM_USE_GCLOUD_TOKEN=false

# Web режим
NOTEBOOKLM_PROFILE=default         # Имя профиля (директория с cookies)
NOTEBOOKLM_AUTH_DIR=~/.notebooklm-mcp  # Директория хранения cookies
NOTEBOOKLM_LANGUAGE=en             # Язык интерфейса (hl параметр)

# Общие
NOTEBOOKLM_TIMEOUT=120             # Таймаут запросов (сек)
NOTEBOOKLM_MAX_RETRIES=3           # Макс. повторы при ошибках
```

---

## Retry и обработка ошибок

| Условие | Действие |
|---|---|
| HTTP 429 / 5xx | Exponential backoff (1s → 2s → 4s → 8s, max 3 попытки) |
| HTTP 401/403, RPC Error 16 | Refresh CSRF/session → reload cookies → headless auth |
| Timeout | Raise `TimeoutError` с понятным сообщением |
| Недоступный инструмент в режиме | Возврат `{"error": "...", "mode": "...", "available_in": "..."}` |

---

## Studio: типы артефактов и коды (web режим)

| Тип | Код | Опции |
|---|---|---|
| audio | 1 | format: 1-4, length: 1-3, language, focus |
| report | 2 | format: briefing/study/blog/custom, custom_prompt |
| video | 3 | format: explainer/brief, visual_style: 1-10 |
| flashcards/quiz | 4 | difficulty, question_count |
| infographic | 7 | orientation, detail_level, style |
| slide_deck | 8 | format: detailed/presenter, length |
| data_table | 9 | description |
| mind_map | — | отдельный RPC (yyryJe) |

**Статусы артефактов:** 1=in_progress, 3=completed, 4=failed

---

## Совместимость с nlm

Профили и cookies хранятся в совместимом формате с `notebooklm-mcp-cli`:

```
~/.notebooklm-mcp-cli/profiles/{profile}/
  cookies.json
  metadata.json
```

При указании `NOTEBOOKLM_AUTH_DIR=~/.notebooklm-mcp-cli` сервер использует существующие сессии без повторного входа.

---

## Фазы реализации

### Фаза 1 — Ядро + Enterprise
- Config, Backend ABC, Enterprise backend
- Auth: ADC, Service Account, gcloud token
- Инструменты: notebooks CRUD, sources, audio_overview, podcast
- FastMCP server

### Фаза 2 — Web backend (базовые операции)
- Cookie auth, CSRF extraction, batchexecute client
- RPC parsers
- Инструменты: notebooks, sources (включая file upload), audio, sharing

### Фаза 3 — Web backend (расширенные)
- Studio (все типы артефактов)
- Research
- Notes
- notebook_query (streaming)
- Exports, downloads
- notebook_describe / source_describe

### Фаза 4 — Полировка
- Совместимость с nlm cookie-профилями
- CDP-based auth extraction из браузера
- Тесты
- Документация CLI
