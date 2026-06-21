// Stable per-browser chat session id, persisted in localStorage.
// Maps server-side to a (session_id, ip) pair used for anonymous quota
// accounting. "Новый диалог" rotates it.

const KEY = 'gurmix_chat_session_id'

function uuid(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for older browsers.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export function getSessionId(): string {
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = uuid()
    localStorage.setItem(KEY, id)
  }
  return id
}

export function resetSession(): string {
  const id = uuid()
  localStorage.setItem(KEY, id)
  return id
}
