# NotebookLM Enterprise — Полная документация API

> Источник: [docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/overview)  
> Статус API: **Preview** (v1alpha)

---

## Содержание

1. [Обзор](#1-обзор)
2. [Настройка](#2-настройка)
3. [Лицензирование](#3-лицензирование)
4. [Аутентификация](#4-аутентификация)
5. [Базовый URL и параметры](#5-базовый-url-и-параметры)
6. [API: Ноутбуки](#6-api-ноутбуки)
7. [API: Источники данных](#7-api-источники-данных)
8. [API: Аудио-обзоры](#8-api-аудио-обзоры)
9. [Podcast API](#9-podcast-api-независимый)
10. [Общий доступ к ноутбукам](#10-общий-доступ-к-ноутбукам)
11. [Model Armor](#11-model-armor)
12. [Аудит-логирование](#12-аудит-логирование)
13. [Шифрование CMEK](#13-шифрование-cmek)
14. [Лимиты и ограничения](#14-лимиты-и-ограничения)

---

## 1. Обзор

NotebookLM Enterprise — корпоративная AI-платформа для анализа документов с поддержкой:

- **VPC-SC** — изоляция данных внутри Google Cloud проекта
- **CMEK** — ключи шифрования под управлением клиента
- **Data residency** — выбор региона хранения (US / EU / global)
- **Model Armor** — фильтрация запросов и ответов
- **Cloud Identity / Workforce Identity Federation** — SSO через Okta, Entra ID, SAML 2.0

### Поддерживаемые форматы источников

| Категория | Форматы |
|---|---|
| Документы | PDF, TXT, MD, DOCX, PPTX, XLSX |
| Google Workspace | Google Docs, Slides; spreadsheet-файлы добавляйте как `.xlsx` upload |
| Медиа | MP3, WAV, AAC, M4A, OGG, FLAC, MP4, WEBM и др. |
| Изображения | PNG, JPG, JPEG |
| Веб | URL, YouTube |

---

## 2. Настройка

### IAM-роли

| Роль | Назначение |
|---|---|
| `Cloud NotebookLM Admin` | Администрирование, настройка |
| `Cloud NotebookLM User` | Создание ноутбуков, доступ к API |
| `Gemini Enterprise Admin` | Управление лицензиями, Model Armor, логами |

### Шаги

1. Создать/выбрать Google Cloud проект с включённым биллингом
2. Включить **Discovery Engine API**
3. Назначить роль `Cloud NotebookLM Admin` администраторам
4. Настроить Identity Provider (Google или сторонний):
   - Для Entra ID / Okta: `google.subject = assertion.email`
5. Назначить пользователям роль `Cloud NotebookLM User` + лицензии

---

## 3. Лицензирование

| Параметр | Значение |
|---|---|
| Минимум лицензий | 15 |
| Максимум лицензий | 5 000 (больше — по запросу) |
| Пробный период | 14 дней / 5 000 лицензий |
| Регион | Лицензии привязаны к мультирегиону (us / eu / global) |

Пользователям, работающим в нескольких регионах, нужны лицензии в каждом регионе.

---

## 4. Аутентификация

Все API-запросы используют Bearer-токен Google Cloud:

```bash
# Получить токен
gcloud auth print-access-token

# Заголовок для всех запросов
Authorization: Bearer $(gcloud auth print-access-token)
Content-Type: application/json
```

Для доступа к Google Drive источникам:

```bash
gcloud auth login --enable-gdrive-access
```

---

## 5. Базовый URL и параметры

```
https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/
```

| Параметр | Возможные значения |
|---|---|
| `ENDPOINT_LOCATION` | `us`, `eu`, `global` |
| `PROJECT_NUMBER` | Номер Google Cloud проекта |
| `LOCATION` | `us`, `eu`, `global` |

**Resource name pattern:**
```
projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID
```

---

## 6. API: Ноутбуки

### 6.1 Создать ноутбук

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks
```

**Тело запроса:**
```json
{
  "title": "NOTEBOOK_TITLE"
}
```

**Ответ:**
```json
{
  "title": "NOTEBOOK_TITLE",
  "notebookId": "NOTEBOOK_ID",
  "emoji": "",
  "metadata": {
    "userRole": "PROJECT_ROLE_OWNER",
    "isShared": false,
    "isShareable": true
  },
  "name": "projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID"
}
```

---

### 6.2 Получить ноутбук

```
GET https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID
```

**Ответ** — аналогичен 6.1, дополнительно содержит поля источников и CMEK.

---

### 6.3 Список недавних ноутбуков

```
GET https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks:listRecentlyViewed
```

**Query параметры:**

| Параметр | Описание |
|---|---|
| `pageSize` | Количество ноутбуков (по умолчанию до 500) |

**Ответ:**
```json
{
  "notebooks": [
    {
      "title": "NOTEBOOK_TITLE",
      "notebookId": "NOTEBOOK_ID",
      "emoji": "",
      "metadata": {
        "userRole": "PROJECT_ROLE_OWNER",
        "isShared": false,
        "isShareable": true,
        "lastViewed": "LAST_VIEWED_TIME",
        "createTime": "LAST_CREATED_TIME"
      },
      "name": "NOTEBOOK_NAME"
    }
  ]
}
```

---

### 6.4 Удалить ноутбуки (batch)

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks:batchDelete
```

**Тело запроса:**
```json
{
  "names": [
    "projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID"
  ]
}
```

**Ответ:** `{}` при успехе.

---

### 6.5 Поделиться ноутбуком

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID:share
```

**Тело запроса:**
```json
{
  "accountAndRoles": [
    {
      "email": "user@example.com",
      "role": "PROJECT_ROLE_READER"
    }
  ]
}
```

**Роли:**

| Роль | Права |
|---|---|
| `PROJECT_ROLE_OWNER` | Полный доступ |
| `PROJECT_ROLE_WRITER` | Редактирование (кроме удаления/шаринга) |
| `PROJECT_ROLE_READER` | Просмотр и взаимодействие |
| `PROJECT_ROLE_NOT_SHARED` | Отозвать доступ |

**Ответ:** `{}` при успехе.

---

## 7. API: Источники данных

### 7.1 Добавить источники (batch)

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/sources:batchCreate
```

**Тело запроса** — массив `userContents` с одним из типов:

#### Google Drive (Docs / Slides)
```json
{
  "userContents": [
    {
      "googleDriveContent": {
        "documentId": "DOCUMENT_ID",
        "mimeType": "application/vnd.google-apps.document",
        "sourceName": "Название документа"
      }
    }
  ]
}
```

MIME-типы:
- Google Docs: `application/vnd.google-apps.document`
- Google Slides: `application/vnd.google-apps.presentation`
- Для таблиц используйте file upload (`.xlsx`) через `sources:uploadFile`, а не `googleDriveContent`.

#### Текст
```json
{
  "userContents": [
    {
      "textContent": {
        "sourceName": "Название",
        "content": "Текстовое содержимое..."
      }
    }
  ]
}
```

#### Веб-страница
```json
{
  "userContents": [
    {
      "webContent": {
        "url": "https://example.com",
        "sourceName": "Название страницы"
      }
    }
  ]
}
```

#### YouTube-видео
```json
{
  "userContents": [
    {
      "videoContent": {
        "youtubeUrl": "https://youtube.com/watch?v=..."
      }
    }
  ]
}
```

**Ответ:**
```json
{
  "sources": [
    {
      "sourceId": {"id": "SOURCE_ID"},
      "title": "Название",
      "metadata": {},
      "settings": {"status": "SOURCE_STATUS_COMPLETE"},
      "name": "projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/source/SOURCE_ID"
    }
  ]
}
```

---

### 7.2 Загрузить файл

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/upload/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/sources:uploadFile
```

**Заголовки:**
```
X-Goog-Upload-File-Name: FILE_DISPLAY_NAME
X-Goog-Upload-Protocol: raw
Content-Type: CONTENT_TYPE
Authorization: Bearer $(gcloud auth print-access-token)
```

**Тело запроса:** бинарное содержимое файла.

**Ответ:**
```json
{
  "sourceId": {"id": "SOURCE_ID"}
}
```

**Поддерживаемые форматы:**

| Тип | Расширения |
|---|---|
| Документы | `.pdf`, `.txt`, `.md`, `.docx`, `.pptx`, `.xlsx` |
| Аудио | `.mp3`, `.wav`, `.aac`, `.m4a`, `.ogg`, `.opus`, `.flac`, `.aiff`, `.amr`, `.wma` |
| Видео | `.mp4`, `.avi`, `.webm`, `.3gp`, `.3g2` |
| Изображения | `.png`, `.jpg`, `.jpeg` |

---

### 7.3 Получить источник

```
GET https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/sources/SOURCE_ID
```

**Ответ:**
```json
{
  "sources": [
    {
      "sourceId": {"id": "SOURCE_ID"},
      "title": "Название",
      "metadata": {"wordCount": 148, "tokenCount": 160},
      "settings": {"status": "SOURCE_STATUS_COMPLETE"},
      "name": "SOURCE_RESOURCE_NAME"
    }
  ]
}
```

---

### 7.4 Удалить источники (batch)

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/sources:batchDelete
```

**Тело запроса:**
```json
{
  "names": [
    "projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/source/SOURCE_ID_1",
    "projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/source/SOURCE_ID_2"
  ]
}
```

**Ответ:** `{}` при успехе.

---

## 8. API: Аудио-обзоры

> Аудио-обзор привязан к ноутбуку с источниками. Для генерации подкаста без ноутбука — см. [Podcast API](#9-podcast-api-независимый).

### 8.1 Создать аудио-обзор

```
POST https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/audioOverviews
```

**Тело запроса:**
```json
{
  "sourceIds": [
    {"id": "SOURCE_ID"}
  ],
  "episodeFocus": "TOPIC_DESCRIPTION",
  "languageCode": "ru"
}
```

> Если `sourceIds` не указан, используются все источники ноутбука.

**Ответ:**
```json
{
  "audioOverview": {
    "status": "AUDIO_OVERVIEW_STATUS_IN_PROGRESS",
    "audioOverviewId": "AUDIO_OVERVIEW_ID",
    "generationOptions": {},
    "name": "projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/audioOverviews/AUDIO_OVERVIEW_ID"
  }
}
```

---

### 8.2 Удалить аудио-обзор

```
DELETE https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER/locations/LOCATION/notebooks/NOTEBOOK_ID/audioOverviews/default
```

**Ответ:** `{}` при успехе.

---

## 9. Podcast API (независимый)

> Не требует ноутбука и корпоративной лицензии. **Не поддерживает CMEK.**

**Роль:** `roles/discoveryengine.podcastApiUser`

### 9.1 Создать подкаст

```
POST https://discoveryengine.googleapis.com/v1/projects/PROJECT_ID/locations/global/podcasts
```

**Тело запроса:**
```json
{
  "podcastConfig": {
    "focus": "Описание темы подкаста",
    "length": "SHORT",
    "languageCode": "ru"
  },
  "contexts": [
    {"text": "Текстовый контент"},
    {
      "inlineData": {
        "mimeType": "application/pdf",
        "data": "BASE64_ENCODED_CONTENT"
      }
    }
  ],
  "title": "Название подкаста",
  "description": "Описание"
}
```

| Параметр `length` | Длительность |
|---|---|
| `SHORT` | 4–5 минут |
| `STANDARD` | ~10 минут |

> Общий объём `contexts` — не более **100 000 токенов**.

**Ответ:**
```json
{
  "name": "projects/PROJECT_ID/locations/global/operations/OPERATION_ID"
}
```

---

### 9.2 Скачать подкаст

```
GET https://discoveryengine.googleapis.com/v1/projects/PROJECT_ID/locations/global/operations/OPERATION_ID:download?alt=media
```

**Ответ:** MP3-файл.

---

## 10. Общий доступ к ноутбукам

### Условия для получателей доступа

- Участник того же Google Cloud проекта
- Наличие роли `Cloud NotebookLM User`
- Наличие лицензии NotebookLM Enterprise или Gemini Enterprise

> Обмен ноутбуками между NotebookLM Enterprise и личным NotebookLM **невозможен**.

### Уровни доступа

| Уровень | Права |
|---|---|
| **Viewer** | Просмотр, взаимодействие. Нельзя добавлять источники и заметки |
| **Editor** | Полный доступ, кроме удаления, шаринга и отзыва доступа |

При нескольких назначениях применяется наивысший уровень.

### Ограничения

- Ноутбуки с контентом из Gemini Enterprise нельзя шарить
- Расшаренным ноутбукам нельзя добавлять источники Gemini Enterprise

---

## 11. Model Armor

Фильтрация запросов и ответов без дополнительной оплаты (увеличивает latency).

**Требуемые роли:**

| Роль | Назначение |
|---|---|
| `Gemini Enterprise Admin` | Включение Model Armor |
| `Model Armor Admin` | Создание шаблонов |
| `Model Armor User` | Вызов API |

### Настройка через API

```bash
curl -X PATCH \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: PROJECT_ID" \
  "https://ENDPOINT_LOCATION-discoveryengine.googleapis.com/v1alpha/projects/PROJECT_NUMBER?update_mask=customerProvidedConfig" \
  -d '{
    "customerProvidedConfig": {
      "notebooklmConfig": {
        "modelArmorConfig": {
          "userPromptTemplate": "QUERY_PROMPT_TEMPLATE",
          "responseTemplate": "RESPONSE_PROMPT_TEMPLATE"
        }
      }
    }
  }'
```

> Шаблоны активируются через **10+ минут** после настройки.

### Соответствие регионов

| Регион NotebookLM | Регион Model Armor |
|---|---|
| `global` | US или EU мультирегион |
| `us` | US мультирегион |
| `eu` | EU мультирегион |

При блокировке запроса в REST-ответе: `"answer.assist_skipped_reasons": "CUSTOMER_POLICY_VIOLATION_REASON"`

---

## 12. Аудит-логирование

**Требуемые роли:**
- `roles/discoveryengine.agentspaceAdmin` — включение логов
- `roles/logging.viewer` — просмотр в Cloud Logging

### Включение

```
PATCH .../v1alpha/projects/PROJECT_NUMBER
```

Установить в `customerProvidedConfig.notebooklmConfig.observabilityConfig`:
- `observabilityEnabled: true`
- `sensitiveLoggingEnabled: true`

> **Внимание:** чувствительные данные не фильтруются из логов.

### Запрос в Logs Explorer

```
resource.type="audited_resource"
resource.labels.service="discoveryengine.googleapis.com"
protoPayload.serviceName="discoveryengine.googleapis.com"
protoPayload.methodName:"NotebookService"
```

### Логируемые операции

Создание, просмотр, удаление ноутбуков, шаринг, работа с источниками, генерация запросов.

---

## 13. Шифрование CMEK

Customer-Managed Encryption Keys через Cloud KMS.

### Ограничения

| Ограничение | Описание |
|---|---|
| Неизменяемость ключа | Ключ нельзя сменить или ротировать после регистрации |
| Только US / EU | Не поддерживается для `global` региона |
| Один ключ на проект | Несколько ключей — только через квоту |
| Terraform | Не поддерживается |
| Podcast API | **Не защищён** CMEK |

### Настройка

1. Создать симметричный Cloud KMS ключ с ручной ротацией (US или EU мультирегион)
2. Назначить роль `CryptoKey Encrypter/Decrypter` для:
   - Discovery Engine service agent
   - Cloud Storage service agent
3. Вызвать `UpdateCmekConfig` через REST API

> При отзыве ключа: данные становятся недоступны в течение **15 минут**.  
> Восстановление после повторного включения — до **24 часов**.

---

## 14. Лимиты и ограничения

| Параметр | Лимит |
|---|---|
| Ноутбуков на пользователя | 500 |
| Источников в ноутбуке | 300 |
| Размер источника | 200 МБ или 500 000 слов |
| Запросов в день на пользователя | 500 |
| Аудио-обзоров в день на пользователя | 20 |
| Видео-обзоров в день на пользователя | 20 |
| Ноутбуков в `listRecentlyViewed` | 500 |
| Токенов в Podcast API contexts | 100 000 |
| Лицензий в подписке | 15–5 000 |

---

## Ссылки

- [NotebookLM Enterprise — обзор](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/overview)
- [API: Ноутбуки](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks)
- [API: Источники](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks-sources)
- [API: Аудио-обзоры](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-audio-overview)
- [Podcast API](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/podcast-api)
- [Discovery Engine REST API Reference](https://cloud.google.com/generative-ai-app-builder/docs/reference/rest)
