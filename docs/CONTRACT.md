# Нейро-шеф Гурмикс — контракт сборки «базы»

Источник истины для фронта (React) и бэка (FastAPI). Оба собираются против этого
документа. Дизайн переносится **1-в-1** из референса `../teplodarbot` (он на Vue —
визуал копируем, логику бэка/RAG повторяем).

## Что это
Веб-чат-бот для компании «Гурмикс» (проф. продукты для кухни). Рабочее название
**«Нейро-шеф Гурмикс»**, эмодзи бренда 👨‍🍳. В вебе — переключение между **8
модулями-экспертами** (см. реестр). Плюс **админка** для RAG (загрузка материалов,
чанки, индекс) и настройки модулей/лимитов.

## Принятые решения (зафиксированы заказчиком)
- **LLM:** Claude **CLI / Pro-подписка** (как в teplodar `src/core/claude_cli.py` +
  `claude_token.py`), НЕ платный API. Модель по умолчанию — **Opus 4.8**
  (`claude-opus-4-8`) и для интента, и для ответа. (В конфиге оставить возможность
  поставить на интент Haiku ради латентности — это коммент, дефолт = opus.)
- **Идентификация для лимитов:** анонимная **сессия (cookie/localStorage) + IP**.
  Логина нет. «Один пользователь» = пара (session_id, ip).
- **Лимиты:** на пользователя — квота **запросов** (первично) и опц. оценка токенов;
  сброс настраивается: **день / неделя / месяц**. Цель — подстраховка, чтобы не
  заспамить Pro-аккаунт. Значения — в конфиге и редактируются в админке.
- **Модули 1–5 — `locked`** (карточка «Скоро»), **6–8 — `active`** (работают через
  Opus). Реестр: `backend/app/modules/registry.py` (бэк, источник истины) и
  `frontend/src/modules.ts` (зеркало публичных полей).

## Раскладка репозитория
```
backend/                      FastAPI
  app/
    core/      config.py, database.py, claude_cli.py, claude_token.py,
               logging.py, migrations.py
    modules/   registry.py (готов)
    rag/       (порт из teplodar src/rag; во 2-й фазе — E5+индекс)
    limits/    models.py, store.py, middleware.py  (НОВОЕ — лимиты)
    api/       routers: chat.py, modules.py, admin/*.py
    schemas/   pydantic-схемы запросов/ответов
    services/  answer service (роутинг на per-module промпт + Claude)
  base/        knowledge base (sqlite, индексы, материалы) — gitkeep
  main.py      приложение FastAPI (lifespan, монтаж роутеров, отдача SPA)
  requirements.txt
  .env.example
frontend/                     React + Vite + TS
  src/
    assets/tokens.css         (готов, 1:1)
    modules.ts                (готов)
    api/index.ts              axios + fetch-SSE клиент
    components/               AppShell, AppSidebar, ChatMessage, ModuleCard, ...
    views/                    ModulePicker, ChatView, admin/*
    App.tsx, main.tsx, router.tsx
  package.json, vite.config.ts, index.html
docs/CONTRACT.md
```
Порты (как в teplodar): **бэк 8001**, **vite 5173** (vite proxy `/api` -> 8001).

## API-контракт (`/api/v1`)

### Модули
- `GET /modules` -> `{ modules: ModulePublic[] }` — публичные карточки из
  `registry.public_list()` (поля: id, title, short, emoji, accent, order, status,
  mode, examples). БЕЗ системных промптов.

### Чат (порт `teplodar admin/routers/chat.py`, но с module_id и лимитами)
- `POST /chat/stream` — **SSE**. Тело:
  `{ module_id: string, message: string, session_id: string, history: {role,content}[] }`.
  Так как Claude CLI не стримит токены — шлём события **фаз**, затем один `done`:
  - `{ "type": "phase", "phase": "intent" | "retrieval" | "answer" }`
  - `{ "type": "done", "answer_html": string, "log_id": number|null, "meta": {...},
       "quota": QuotaState }`
  - `{ "type": "error", "message": string }`
  - `{ "type": "limit", "message": string, "quota": QuotaState }` — лимит исчерпан
    (HTTP всё равно 200, фронт показывает баннер «лимит исчерпан»).
  Рамка SSE: `data: <json>\n\n` (как teplodar `frontend/src/api/index.js`
  `sendChatStream`). Заголовки: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
- `POST /chat/feedback` -> `{ log_id, feedback: "good"|"bad", note?: string }`.

`meta` (debug-чип): `{ module_id, query_type, top_score, chunks_used,
t_intent_ms, t_retrieval_ms, t_answer_ms, t_answer_model, latency_ms }`.

### Лимиты / квоты
`QuotaState = { used: number, limit: number, remaining: number, period: "day"|"week"|"month", reset_at: string(ISO), blocked: boolean }`.
- `GET /quota?session_id=...` -> текущая `QuotaState` для (session_id, ip).
- Идентификация: `session_id` из тела/квери + IP из запроса. Хранилище — SQLite
  таблица `usage_counters(session_id, ip, period_start, count, est_tokens)`.
  Enforcement — зависимость/middleware на `/chat/stream`: до запуска пайплайна
  проверяет квоту; если `remaining<=0` — отдаёт SSE `limit` и не вызывает Claude.
  При успешном ответе инкрементит счётчик (и опц. += оценка токенов).
- Конфиг по умолчанию (в `core/config.py`, правится в админке):
  `quota_limit=30`, `quota_period="day"` (значения ориентировочные).

### Админка (`/api/v1/admin/...`, под basic-auth как teplodar)
Во 2-й фазе подробно; в «базе» — скелет, который работает и расширяется:
- `GET/POST /admin/modules` — список модулей + правка `status`/настроек.
- `GET /admin/quota/config`, `PUT /admin/quota/config` — лимит/период.
- Документы/RAG (порт teplodar `documents`, `chunks`, `pipeline`): `POST
  /admin/documents/upload`, `GET /admin/documents`, `GET /admin/chunks`,
  `POST /admin/pipeline/rebuild-index`. В «базе» можно отдать заглушки-501 с
  корректной формой ответа, чтобы UI рендерился; реальная ингестия — фаза 2.
- Дистрибьюторы (модуль 8): `GET/POST/DELETE /admin/distributors`.
- Журнал: `GET /admin/journal` (порт teplodar `query_logs`).

## Claude CLI (бэк)
Портировать из teplodar `src/core/claude_cli.py` (subprocess `claude --print
--output-format text --no-session-persistence --model <id>`, file-lock slot-pool на
N слотов, per-call TemporaryDirectory как cwd) и `claude_token.py` (авто-рефреш
OAuth `data/.claude_token.json`). `core/config.py`: `claude_model=claude-opus-4-8`,
`claude_intent_model=claude-opus-4-8` (коммент: Haiku=`claude-haiku-4-5` быстрее),
`claude_cli_max_concurrent=4`, slots dir `/tmp/gurmix_claude_slots`.

В «базе» активные модули (6–8) отвечают режимом `llm`: системный промпт модуля
(`Module.full_system_prompt`) + история + вопрос -> Claude CLI -> HTML-ответ.
RAG-подмешивание корпуса — фаза 2 (порт `src/rag`). Модуль 8 (`db`) — отвечает из
таблицы дистрибьюторов; если пусто — текст «оставьте заявку».

## Дизайн (1-в-1, обязательно)
Токены: `frontend/src/assets/tokens.css` (готов, не менять значения). Шрифты Inter
+ JetBrains Mono. Светлая тема, синий акцент `--accent`.

Референс-файлы в `../teplodarbot/admin/frontend/src` — повторить структуру/стиль:
- `App.vue` -> `App.tsx`: два layout'а. `chat` (полноэкранный, без сайдбара,
  работает на телефоне) и `admin` (грид `240px 1fr`, topbar 52px, min-width 1180px).
  Тосты в правом-верхнем углу (`.toast`, типы success/error/info).
- `views/ChatView.vue` -> `views/ChatView.tsx`: одна колонка `max-width 760px`,
  header с брендом + «+ Новый диалог», empty-state с эмодзи/заголовком/подсказкой
  и кнопками-примерами (берём `examples` модуля), textarea c autogrow (Enter —
  отправить, Shift+Enter — перенос), круглая синяя кнопка отправки, hint снизу.
  Стриминг — через `sendChatStream` (fetch + ReadableStream, парсинг SSE по `\n\n`).
- `components/ChatMessage.vue` -> `ChatMessage.tsx`: рендер ответа `dangerouslySet
  InnerHTML` через мини-санитайзер (allowlist `b,i,code,a,br` + linkify URL/тел.),
  👍/👎 + инлайн-заметка на 👎, meta-чип со score/таймингами.
- `components/AppSidebar.vue` -> `AppSidebar.tsx`: бренд «Нейро-шеф Гурмикс» 👨‍🍳,
  nav для админки (Dashboard, Документы, RAG Чанки, Модули, Дистрибьюторы, Лимиты,
  Журнал). Активный пункт: белый фон + акцентный текст + тень.
- `components/AppShell.vue` -> `AppShell.tsx`: сайдбар + topbar + `<main>` с
  `<RouterView/>`/`<Outlet/>`.
- `api/index.js` -> `api/index.ts`: axios baseURL `/api/v1` + `sendChatStream`.

### НОВЫЙ экран — выбор модуля (ModulePicker)
Главный экран чат-приложения (`/`): сетка из 8 карточек-экспертов (`ModuleCard`).
Карточка: эмодзи в кружке акцент-цвета (`var(<accent>)`), title, short. `active`
кликабельна -> переход в чат модуля. `locked` — приглушена + бейдж «Скоро»
(`--status-new-bg/fg`), не кликается. Чистый light-CRM-стиль из токенов, скругления
`--rad-lg`, тень `--shadow-1`, hover `--shadow-2`.

### Роутинг
- `/` — ModulePicker (layout `chat`).
- `/m/:moduleId` — ChatView для модуля (layout `chat`). Бренд в header =
  emoji+title модуля; примеры в empty-state = `module.examples`.
- `/admin`, `/admin/*` — админка (layout `admin`), как в teplodar.

## Definition of done для «базы»
1. `cd frontend && npm i && npm run build` — без ошибок; `npm run dev` поднимает UI.
2. `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8001`
   стартует; `GET /api/v1/modules` отдаёт 8 модулей; `POST /api/v1/chat/stream` для
   активного модуля (6–8) реально зовёт Claude CLI и отдаёт `phase...done`; лимит
   срабатывает после `quota_limit` запросов и шлёт `limit`.
3. ModulePicker показывает 8 карточек (5 locked «Скоро», 3 active), чат активного
   модуля работает end-to-end через vite-proxy.
4. Админ-скелет открывается на `/admin` (страницы Модули/Лимиты/Документы/
   Дистрибьюторы/Журнал; данные/заглушки по контракту).
