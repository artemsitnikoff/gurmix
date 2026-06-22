// Рендер ответа бота: Markdown → безопасный HTML.
//
// Модель (Opus) возвращает Markdown. Бэкенд проксирует его как есть в поле
// answer_html; здесь мы превращаем Markdown в HTML (marked, GFM) и санитизируем
// (DOMPurify) — это граница безопасности перед dangerouslySetInnerHTML.

import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ gfm: true, breaks: true })

// Узкий allowlist под то, что генерит Markdown-ответ.
const ALLOWED_TAGS = [
  'p', 'br', 'hr', 'strong', 'em', 'b', 'i', 'del', 's', 'code', 'pre',
  'blockquote', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
]
const ALLOWED_ATTR = ['href', 'title', 'target', 'rel']

// Внешние ссылки — всегда в новой вкладке и без доступа к window.opener.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/** Markdown-текст ответа → отсанитизированный HTML для dangerouslySetInnerHTML. */
export function renderAnswer(md: string): string {
  if (!md) return ''
  const rawHtml = marked.parse(md, { async: false }) as string
  return DOMPurify.sanitize(rawHtml, { ALLOWED_TAGS, ALLOWED_ATTR })
}
