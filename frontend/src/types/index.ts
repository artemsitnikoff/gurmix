// Shared TypeScript types for the Гурмикс frontend.

export type ChatRole = 'user' | 'assistant'

export type ChatPhase = 'intent' | 'retrieval' | 'answer'

export type HistoryTurn = { role: ChatRole; content: string }

export type ChatMeta = {
  module_id?: string
  query_type?: string
  top_score?: number | null
  chunks_used?: number
  t_intent_ms?: number
  t_retrieval_ms?: number
  t_answer_ms?: number
  t_answer_model?: string
  latency_ms?: number
}

export type QuotaState = {
  used: number
  limit: number
  remaining: number
  period: 'day' | 'week' | 'month'
  reset_at: string
  blocked: boolean
}

// SSE event from POST /chat/stream.
export type DoneEvent = {
  type: 'done'
  answer_html: string
  log_id: number | null
  meta: ChatMeta | null
  quota?: QuotaState
}

export type LimitEvent = {
  type: 'limit'
  message: string
  quota?: QuotaState
}

// In-memory chat message used by ChatView / ChatMessage.
export type ChatMessageModel = {
  id: number
  role: ChatRole
  content: string
  pending?: boolean
  phase?: ChatPhase
  isError?: boolean
  meta?: ChatMeta | null
  logId?: number | null
  feedback?: 'good' | 'bad' | null
}
