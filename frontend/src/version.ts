// Версия приложения. Единый источник истины — файл VERSION в корне репозитория;
// значение подставляется на сборке через vite `define` (см. vite.config.ts) и
// авто-бампается git-хуком .githooks/pre-commit на каждом коммите. Бэкенд читает
// тот же VERSION в рантайме (app/core/version.py).
export const APP_VERSION: string = __APP_VERSION__
