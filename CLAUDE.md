# Нейро-шеф Гурмикс — контекст проекта

Веб-чат-бот для компании «Гурмикс» (профессиональные продукты для кухни). В вебе —
переключение между **8 модулями-экспертами**; плюс **админка** для управления базой
знаний (RAG) и настройки модулей/лимитов. Дизайн перенесён **1-в-1** из референса
`../teplodarbot` (он на Vue — копируем визуал, в React).

## Архитектура
- **Frontend:** React + Vite + TypeScript (`frontend/`). Дизайн-токены
  `src/assets/tokens.css` (Inter + JetBrains Mono, светлая CRM-тема, синий акцент).
  Чат одной колонкой (как ChatGPT) + админка с сайдбаром. SSE-стрим фаз.
- **Backend:** FastAPI (`backend/app/`). Роутеры под `/api/v1`. Отдаёт собранный
  SPA из `frontend/dist`, если есть.
- **LLM:** **Claude CLI (Pro-подписка через OAuth, НЕ платный API)** —
  `app/core/claude_cli.py` (subprocess `claude --print …`, fcntl slot-pool на N
  слотов) + `claude_token.py` (авто-рефреш `data/.claude_token.json`). Модель по
  умолчанию — **Opus 4.8** (`claude-opus-4-8`) на интент и ответ; **LLM-судья**
  (оценка полезности ответа в фоне) — **Haiku** (`claude_judge_model`).
- **RAG:** база знаний (SQLite `base/gurmix.db`); гибрид BM25+dense на E5 — **фаза 2**
  (порт из teplodar `src/rag`). Сейчас активные модули отвечают в режиме `llm` без
  корпуса, в демо-режиме `expert_mode` (экспертная преамбула вместо GUARDRAIL).
- **Ответы — Markdown:** модель возвращает Markdown, бэк отдаёт его как есть в
  `answer_html`, фронт рендерит `marked`(GFM)+`DOMPurify` (`utils/sanitizeHtml.ts`).

## Ключевые решения (согласованы с заказчиком)
- LLM = **Claude CLI / Pro**, не API (бюджет не висит per-token).
- **Лимиты на пользователя:** идентификация — **анонимная сессия (cookie/localStorage)
  + IP** (логина нет). Квота запросов со сбросом **день/неделя/месяц**, настраивается
  в админке. Подстраховка Pro-аккаунта. В teplodar лимитов не было — это новое
  (`app/limits/`).
- **8 модулей** — реестр `backend/app/modules/registry.py` (источник истины) +
  зеркало `frontend/src/modules.ts`. Модули **1–5 = locked** («Скоро»), **6–8 = active**.
- **Бот НЕ выдумывает** продукты/составы/нормы/цены/дистрибьюторов. У RAG-модулей —
  преамбула `GUARDRAIL` (строго из базы, иначе «оставьте заявку»); у активных
  демо-модулей (`expert_mode=True`) — `EXPERT_PREAMBLE`: отвечает уверенно как эксперт
  на общих знаниях, но не выдумывает конкретику Гурмикс (артикулы/цены/контакты).
  Модуль 8 на демо переведён `db→llm` (ветка `_answer_db` дремлет до реальных данных).

## Запуск (dev)
```bash
# Бэк (порт 8001)
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # задать ADMIN_PASS; для модулей 6/7 нужен залогиненный `claude` CLI
.venv/bin/uvicorn app.main:app --port 8001
# Фронт (vite 5173, проксит /api -> 8001)
cd frontend && npm install && npm run dev
```
Порты: **8001** — бэк, **5173** — vite. Прод: один сервис на `APP_PORT` (см. DEPLOY.md).

## Деплой
`docker compose up -d --build`. Один сервис `web` на **`APP_PORT` (дефолт 8420,
нестандартный)**. `data/` на проде — симлинк на `/var/www/ArkadiyJarvis/data`
(общий Claude-токен). **Релиз = `git push origin main`** → GitHub Actions
(`.github/workflows/deploy.yml`) по SSH пересобирает `web` на VPS (секреты
`SSH_HOST`/`SSH_USER`/`SSH_PRIVATE_KEY`/`DEPLOY_PATH`). Полный чеклист — **`DEPLOY.md`**.

## Версионность
Единый источник истины — файл **`VERSION`** в корне (semver `MAJOR.MINOR.PATCH`).
Git-хук **`.githooks/pre-commit`** авто-бампает PATCH на каждом коммите и
`git add`-ит `VERSION`; **`.githooks/prepare-commit-msg`** ставит префикс `vX.Y.Z `
в сообщение коммита (история git = ченджлог, как в glafira). Включить один раз:
`sh scripts/setup-hooks.sh` (ставит `core.hooksPath=.githooks`). Пропустить бамп —
`GURMIX_NO_BUMP=1 git commit …`. Версию читают: фронт — на сборке через
`vite define` → `src/version.ts` (`APP_VERSION`; виден в шапке лендинга и сайдбаре
админки), бэк — `app/core/version.py` в рантайме (`/health`, `GET /api/v1/version`,
версия в `/docs`). В Docker `VERSION` копируется в образ (stage 1 `/VERSION` для
vite, stage 2 `/app/VERSION` для бэка).

## Структура
```
backend/app/
  core/      config, database, claude_cli (slot-pool), claude_token (OAuth refresh),
             logging, migrations (schema probe)
  modules/   registry.py — 8 модулей с персонами + GUARDRAIL
  limits/    models.py (usage_counters), store.py (квоты session+IP, day/week/month)
  services/  answer.py — роутинг module_id -> промпт -> Claude CLI -> (md, meta);
             judge.py — LLM-судья полезности (Haiku, в фоне)
  schemas/   pydantic (ChatRequest, QuotaState, Distributor…)
  api/       modules.py, chat.py (SSE + фоновый судья), admin/ (basic-auth: modules,
             quota, documents, chunks, pipeline, distributors CRUD, journal + context)
  main.py    FastAPI app (lifespan, /api/v1, /health, /api/v1/version, отдача SPA)
frontend/src/
  modules.ts, version.ts, assets/tokens.css, api/index.ts (axios + sendChatStream),
  utils/sanitizeHtml.ts (renderAnswer: marked+DOMPurify),
  components/ (AppShell, AppSidebar, ModuleCard, ChatMessage, Toast),
  views/ (ModulePicker, ChatView, admin/* — AdminJournal с судьёй и нитью диалога)
VERSION                       — источник истины версии (бампается .githooks/pre-commit)
.githooks/                    — pre-commit (авто-бамп) + prepare-commit-msg (vX.Y.Z)
.github/workflows/deploy.yml  — CI: push в main → деплой на VPS по SSH
scripts/setup-hooks.sh        — одноразовое включение git-хуков (core.hooksPath)
docs/CONTRACT.md   — контракт API/SSE/дизайна (источник истины сборки)
```

## API (`/api/v1`) — кратко
- `GET /modules` -> 8 публичных карточек.
- `POST /chat/stream` -> SSE: `phase`(intent→retrieval→answer) → `done`{answer_html,
  log_id, meta, quota} / `error` / `limit`. Тело: {module_id, message, session_id, history}.
  `answer_html` несёт **Markdown** модели (рендер на фронте). После `done` в фоне
  запускается **LLM-судья** → пишет `usefulness_score/verdict` в строку журнала.
- `POST /chat/feedback`, `GET /quota`, `GET /version`.
- `/admin/*` (basic-auth): modules, quota config, documents/chunks/pipeline (501 —
  фаза 2), distributors CRUD, journal (`GET /admin/journal` + `GET /admin/journal/{id}/context`
  — нить диалога; в записях есть оценка судьи `usefulness_*`).
Полностью — `docs/CONTRACT.md`.

## Состояние
**Готово (фаза 1 «база» + демо, на проде `v0.1.2`):** каркас фронта+бэка, дизайн 1:1,
экран выбора 8 модулей, чат активных модулей (6–8) через Claude CLI с SSE, лимиты
(session+IP, day/week/month), скелет админки, Docker-деплой. Сверх каркаса:
- **Markdown-ответы:** бэк проксирует Markdown модели в `answer_html`, фронт рендерит
  `renderAnswer` (`marked` GFM + `DOMPurify`, `src/utils/sanitizeHtml.ts`).
- **Демо-режим 6/7/8:** `llm` + `expert_mode` → `EXPERT_PREAMBLE` вместо `GUARDRAIL`
  (уверенный эксперт, без выдумки конкретики Гурмикс). Модуль 8 — `db→llm`.
- **Журнал + LLM-судья:** `services/judge.py` (Haiku, в фоне после ответа, JSON
  `score 0-100 + verdict`) → колонки `usefulness_*`; админ-журнал = пилюля судьи +
  деталь + нить диалога (`/admin/journal/{id}/context`), пагинация.
- **Версионность + CI:** `VERSION` + git-хуки авто-бампа; push в `main` → автодеплой
  на VPS (`.github/workflows/deploy.yml`). См. разделы «Версионность», «Деплой».

**Фаза 2 (TODO):**
- Порт RAG-ингестии (E5 + индекс) в админку; подмешивание корпуса в `answer.py` для
  RAG-модулей. Сейчас `/admin/documents`, `/admin/pipeline/rebuild-index` — 501.
- ТТК-Excel генератор (модуль 4, openpyxl).
- Трендовый блок (модуль 7): выбрать схему — загруженные материалы / внешний поиск /
  гибрид.
- Реальные данные дистрибьюторов + матчинг по региону (вернуть модуль 8 в `db`/RAG —
  ветка `_answer_db` готова и уже отдаёт Markdown).
- Персист статуса модуля из админки (сейчас in-memory), реальный intent-роутинг
  (сейчас заглушка), интент на Haiku ради латентности, наполнение базы знаний
  материалами Гурмикс, разблокировка модулей 1–5.

## Грабли
- Агенты `react-expert`/`fastapi-expert` имеют в frontmatter недоступную модель
  `claude-sonnet-4-20250514` — при запуске через Workflow/Agent передавай
  `model: 'opus'` (или sonnet/haiku), иначе мгновенный фейл «model may not exist».
- `claude` CLI в контейнере авторизуется через env `CLAUDE_CODE_OAUTH_TOKEN`
  (проставляется из `data/.claude_token.json`). `data/` на проде — симлинк, в
  `.dockerignore` (иначе COPY затащит битый симлинк).
- Локально может быть включён HTTP-прокси — для loopback-тестов через httpx шли
  `NO_PROXY='*'` (на сам сервис не влияет).
- Порт прода — `APP_PORT` (одна переменная меняет host и контейнер).
