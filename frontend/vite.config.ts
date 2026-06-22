import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'

// Версия — единый источник истины: файл VERSION в корне репо (бампается git-хуком
// .githooks/pre-commit). Подставляется в бандл как глобальная __APP_VERSION__.
function readVersion(): string {
  try {
    const raw = readFileSync(fileURLToPath(new URL('../VERSION', import.meta.url)), 'utf-8')
    return raw.trim() || '0.0.0'
  } catch {
    return '0.0.0'
  }
}

// Vite dev server proxies /api -> FastAPI backend (port 8001), as in teplodar.
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(readVersion()),
  },
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
