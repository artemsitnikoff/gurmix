# Деплой «Нейро-шеф Гурмикс»

Один web-сервис в `docker-compose`:
- **web** — FastAPI + собранный React SPA + Claude CLI, на порту `APP_PORT` (по
  умолчанию **8420** — нестандартный, т.к. на проде много чего занято).

Сервис использует тома:
- `./base` — база знаний (SQLite; в фазе 2 добавятся эмбеддинги/индекс/материалы)
- `./data` — **shared с ArkadiyJarvis** (Claude OAuth-токен `data/.claude_token.json`)

> LLM работает через **Claude CLI (Pro-подписка, не платный API)** — отдельный
> API-ключ Anthropic НЕ нужен, нужен общий OAuth-токен Pro-аккаунта (как у teplodar).

## Требования к серверу
- Docker + Docker Compose
- ~1–2 ГБ свободно (в фазе 2, когда подключим RAG/E5, потребуется ещё ~1.5 ГБ)
- Исходящий доступ к `api.anthropic.com`, `registry.npmjs.org`, `deb.nodesource.com`
  (последние два — только на время сборки образа)

## Первоначальная установка

### 1. Клонировать и настроить `.env`
```bash
git clone <repo-url> gurmix
cd gurmix
cp .env.example .env
nano .env
# Обязательно: APP_PORT (если 8420 занят — поставь свободный), ADMIN_PASS.
# CLAUDE_* можно оставить пустыми, если общий токен берётся из data/ (шаг 3).
```

### 2. Перенести базу знаний (папка `base/`), если уже есть
В «базе» (фаза 1) бот наполняет SQLite сам при старте. Когда появятся
эмбеддинги/материалы (фаза 2) — копируй их с Mac:
```bash
# пример (фаза 2):
scp backend/base/gurmix.db user@server:~/gurmix/base/
```
> Том монтируется в корень репо как `./base` (не `backend/base`). На сервере
> создай `mkdir -p base` если её нет.

### 3. Настроить shared `data/` с ArkadiyJarvis (общий Claude-токен)
ArkadiyJarvis на проде живёт в **`/var/www/ArkadiyJarvis`**. Папка `data/` в корне
gurmix должна быть **симлинком** на data ArkadiyJarvis — НЕ делай `mkdir data`,
иначе будут два независимых OAuth-токена, и они затрут друг друга при рефреше.
```bash
# ОДИН раз при первом деплое:
ln -s /var/www/ArkadiyJarvis/data ./data
# проверить, что токен виден:
ls -la data/.claude_token.json
```
Если ArkadiyJarvis ещё не задеплоен (он первичный держатель токена) — подними его
первым, потом симлинкуй сюда. Либо при первом деплое заполни `CLAUDE_CODE_OAUTH_TOKEN`
+ `CLAUDE_REFRESH_TOKEN` в `.env` — при старте они запишутся в
`data/.claude_token.json` и дальше обновляются автоматически.

### 4. Запустить
```bash
docker compose up -d --build
```
Первая сборка ~2–4 мин (Node + Claude CLI + сборка фронта + pip).

### 5. Проверка
```bash
curl localhost:${APP_PORT:-8420}/health                 # {"status":"healthy"}
curl localhost:${APP_PORT:-8420}/api/v1/modules         # 8 модулей
docker compose ps                                       # healthy
docker compose logs -f web
```
Веб: `http://server:<APP_PORT>/` — экран выбора 8 модулей; админка `…/admin`.

## Обновление
```bash
cd ~/gurmix && git pull && docker compose up -d --build
```
Если `requirements.txt` и `frontend/package.json` не менялись — пересборка быстрая
(слои из кэша).

## Смена порта (если выбранный занят)
Порт задаётся ОДНОЙ переменной — `APP_PORT` в `.env` (и host-, и container-порт):
```bash
nano .env            # APP_PORT=9137  (любой свободный)
docker compose up -d --build
```

## Reverse-proxy (опционально)
Поставь nginx/Caddy сверху и проксируй на `127.0.0.1:<APP_PORT>`. Для SSE-чата
важно отключить буферизацию ответа (бэк уже шлёт `X-Accel-Buffering: no`):
```nginx
location / {
    proxy_pass http://127.0.0.1:8420;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;     # критично для SSE-стрима чата
    proxy_read_timeout 300s;
}
```

## Полезные команды
```bash
docker compose logs -f web      # логи
docker compose restart web      # рестарт без пересборки
docker compose down             # остановить
docker compose ps               # статус/health
docker compose exec web bash    # шелл в контейнере
```

## Бэкап
```bash
# SQLite (товары/дистрибьюторы/журнал/счётчики квот):
scp user@server:~/gurmix/base/gurmix.db ./backup_$(date +%Y%m%d).db
```
Claude-токен `data/.claude_token.json` трогать не нужно (автообновляется, общий
с ArkadiyJarvis).

## Структура томов
```
base/
  gurmix.db                  # SQLite: дистрибьюторы, журнал, usage_counters (квоты)
  (фаза 2: эмбеддинги *.npy, метаданные *.pkl, материалы/pdfs)
data/                        # symlink -> /var/www/ArkadiyJarvis/data
  .claude_token.json         # Claude OAuth-токен (автообновление, общий)
```

## Нюансы
- **Claude CLI в контейнере** авторизуется через env `CLAUDE_CODE_OAUTH_TOKEN`,
  который приложение проставляет из `data/.claude_token.json` перед каждым вызовом.
  Без валидного токена старт/`/health`/`/modules`/квоты работают, но активные
  модули (6–8, режим llm) вернут SSE-`error` с понятным текстом.
- **Модуль `distributors`** (mode=db) работает без Claude — отвечает из таблицы
  дистрибьюторов; при пустой базе по региону честно предлагает оставить заявку.
- **Фаза 2 (RAG):** когда подключим E5/индекс — в образ добавятся torch/
  transformers (тяжелее), и в `docker-compose.yml` появится том
  `hf_cache:/root/.cache/huggingface` для кэша модели. Сейчас его нет — образ лёгкий.
