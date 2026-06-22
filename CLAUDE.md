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
  умолчанию — **Opus 4.8** (`claude-opus-4-8`) и на интент, и на ответ.
- **RAG:** база знаний (SQLite `base/gurmix.db`); гибрид BM25+dense на E5 — **фаза 2**
  (порт из teplodar `src/rag`). Сейчас активные модули отвечают в режиме `llm` без
  корпуса.

## Ключевые решения (согласованы с заказчиком)
- LLM = **Claude CLI / Pro**, не API (бюджет не висит per-token).
- **Лимиты на пользователя:** идентификация — **анонимная сессия (cookie/localStorage)
  + IP** (логина нет). Квота запросов со сбросом **день/неделя/месяц**, настраивается
  в админке. Подстраховка Pro-аккаунта. В teplodar лимитов не было — это новое
  (`app/limits/`).
- **8 модулей** — реестр `backend/app/modules/registry.py` (источник истины) +
  зеркало `frontend/src/modules.ts`. Модули **1–5 = locked** («Скоро»), **6–8 = active**.
- **Бот НЕ выдумывает** продукты/составы/нормы/цены/дистрибьюторов — преамбула
  `GUARDRAIL` в каждом системном промпте; при отсутствии данных — «оставьте заявку».

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
  services/  answer.py — роутинг module_id -> промпт -> Claude CLI -> (html, meta)
  schemas/   pydantic (ChatRequest, QuotaState, Distributor…)
  api/       modules.py, chat.py (SSE), admin/ (basic-auth: modules, quota, documents,
             chunks, pipeline, distributors CRUD, journal)
  main.py    FastAPI app (lifespan, /api/v1, /health, отдача SPA)
frontend/src/
  modules.ts, assets/tokens.css, api/index.ts (axios + sendChatStream),
  components/ (AppShell, AppSidebar, ModuleCard, ChatMessage, Toast),
  views/ (ModulePicker, ChatView, admin/*)
docs/CONTRACT.md   — контракт API/SSE/дизайна (источник истины сборки)
```

## API (`/api/v1`) — кратко
- `GET /modules` -> 8 публичных карточек.
- `POST /chat/stream` -> SSE: `phase`(intent→retrieval→answer) → `done`{answer_html,
  log_id, meta, quota} / `error` / `limit`. Тело: {module_id, message, session_id, history}.
- `POST /chat/feedback`, `GET /quota`.
- `/admin/*` (basic-auth): modules, quota config, documents/chunks/pipeline (501 —
  фаза 2), distributors CRUD, journal.
Полностью — `docs/CONTRACT.md`.

## Состояние
**Готово (фаза 1 «база»):** каркас фронта+бэка, дизайн 1:1, экран выбора 8 модулей,
чат активных модулей (6–8) через Claude CLI с SSE, подсистема лимитов (session+IP,
day/week/month), скелет админки, модуль `distributors` из БД, Docker-деплой.
Проверено end-to-end: `/modules`=8, SSE-конвейер, инкремент квоты, `npm run build`.

**Фаза 2 (TODO):**
- Порт RAG-ингестии (E5 + индекс) в админку; подмешивание корпуса в `answer.py` для
  RAG-модулей. Сейчас `/admin/documents`, `/admin/pipeline/rebuild-index` — 501.
- ТТК-Excel генератор (модуль 4, openpyxl).
- Трендовый блок (модуль 7): выбрать схему — загруженные материалы / внешний поиск /
  гибрид.
- Реальные данные дистрибьюторов + матчинг по региону.
- Персист статуса модуля из админки (сейчас in-memory), интент на Haiku ради
  латентности, наполнение базы знаний материалами Гурмикс, разблокировка модулей 1–5.

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
