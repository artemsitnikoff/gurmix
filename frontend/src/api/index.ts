import axios from 'axios'
import type {
  ChatMeta,
  DoneEvent,
  HistoryTurn,
  LimitEvent,
  QuotaState,
} from '@/types'
import type { BotModule } from '@/modules'

// Axios client — baseURL /api/v1 (vite proxy → FastAPI :8001).
const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

if (import.meta.env.DEV) {
  client.interceptors.request.use((config) => {
    console.log(`[api] → ${config.method?.toUpperCase()} ${config.url}`)
    return config
  })
  client.interceptors.response.use(
    (resp) => {
      console.log(`[api] ← ${resp.status} ${resp.config.url}`)
      return resp
    },
    (err) => {
      console.error(`[api] FAIL ${err.response?.status ?? 'ERR'} ${err.config?.url}`)
      return Promise.reject(err)
    },
  )
}

// ── Public endpoints ──────────────────────────────────────────────────
export const api = {
  // Modules — public cards from registry.public_list().
  getModules: () => client.get<{ modules: BotModule[] }>('/modules'),

  // Quota for the current (session_id, ip).
  getQuota: (sessionId: string) =>
    client.get<QuotaState>('/quota', { params: { session_id: sessionId } }),

  // Chat feedback (👍/👎 + optional note).
  sendChatFeedback: (payload: {
    log_id: number
    feedback: 'good' | 'bad'
    note?: string | null
  }) => client.post('/chat/feedback', payload),

  // ── Admin ───────────────────────────────────────────────────────────
  adminGetModules: () => client.get('/admin/modules'),
  adminUpdateModule: (id: string, data: Record<string, unknown>) =>
    client.post('/admin/modules', { id, ...data }),

  adminGetQuotaConfig: () => client.get('/admin/quota/config'),
  adminUpdateQuotaConfig: (data: { limit: number; period: string }) =>
    client.put('/admin/quota/config', data),

  adminGetDocuments: (params: Record<string, unknown> = {}) =>
    client.get('/admin/documents', { params }),
  adminUploadDocument: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return client.post('/admin/documents/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  adminGetChunks: (params: Record<string, unknown> = {}) =>
    client.get('/admin/chunks', { params }),
  adminRebuildIndex: () => client.post('/admin/pipeline/rebuild-index'),

  adminGetDistributors: () => client.get('/admin/distributors'),
  adminCreateDistributor: (data: Record<string, unknown>) =>
    client.post('/admin/distributors', data),
  adminDeleteDistributor: (id: number) => client.delete(`/admin/distributors/${id}`),

  adminGetJournal: (params: Record<string, unknown> = {}) =>
    client.get('/admin/journal', { params }),
}

// ── Streaming chat ────────────────────────────────────────────────────
// Native fetch + ReadableStream: axios doesn't surface a streaming body in
// the browser, and we need a POST body (EventSource is out). SSE frames are
// separated by a blank line; each carries `data: <json>`. Claude CLI doesn't
// token-stream, so the backend emits phase events then one done/limit/error.
type StreamBody = {
  module_id: string
  message: string
  session_id: string
  history: HistoryTurn[]
}

type StreamHandlers = {
  onPhase?: (phase: string) => void
  onDone?: (ev: DoneEvent) => void
  onError?: (err: Error, ev?: { type: string; message?: string }) => void
  onLimit?: (ev: LimitEvent) => void
  signal?: AbortSignal
}

export async function sendChatStream(
  { module_id, message, session_id, history }: StreamBody,
  { onPhase, onDone, onError, onLimit, signal }: StreamHandlers = {},
): Promise<void> {
  try {
    const resp = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ module_id, message, session_id, history }),
      signal,
    })
    if (!resp.ok || !resp.body) {
      onError?.(new Error(`HTTP ${resp.status}`))
      return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      // SSE frames are separated by a blank line.
      let sep: number
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)
        const dataLine = frame.split('\n').find((l) => l.startsWith('data:'))
        if (!dataLine) continue
        const payload = dataLine.slice(5).trim()
        if (!payload) continue
        let ev: { type: string; phase?: string; message?: string } & Record<string, unknown>
        try {
          ev = JSON.parse(payload)
        } catch {
          continue
        }
        if (ev.type === 'phase') onPhase?.(ev.phase as string)
        else if (ev.type === 'done') onDone?.(ev as unknown as DoneEvent)
        else if (ev.type === 'limit') onLimit?.(ev as unknown as LimitEvent)
        else if (ev.type === 'error')
          onError?.(new Error(ev.message || 'stream error'), ev as { type: string; message?: string })
      }
    }
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') return
    onError?.(e as Error)
  }
}

export type { ChatMeta }
export default client
