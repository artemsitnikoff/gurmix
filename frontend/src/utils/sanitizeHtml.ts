// Minimal sanitizer for bot answers.
//
// Answers arrive as a constrained subset of HTML produced by the backend
// (<b>, <i>, <code>, plain URLs, newlines). We escape everything, then
// re-enable only that allowlist and linkify URLs / phone numbers. No
// external dependency — the output is our own LLM's narrow tag set.

const ALLOWED = ['b', 'strong', 'i', 'em', 'code', 'br']

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function restoreAllowedTags(s: string): string {
  for (const tag of ALLOWED) {
    s = s
      .replace(new RegExp(`&lt;${tag}&gt;`, 'gi'), `<${tag}>`)
      .replace(new RegExp(`&lt;/${tag}&gt;`, 'gi'), `</${tag}>`)
      .replace(new RegExp(`&lt;${tag}\\s*/&gt;`, 'gi'), `<${tag}>`)
  }
  return s
}

// URL up to the next space or tag boundary, minus trailing punctuation.
const URL_RE = /(https?:\/\/[^\s<]+[^\s<.,;:!?)\]])/gi

// RU phone like 8 800 775-03-07 / +7 (999) 303-09-27 — link to tel:.
const PHONE_RE = /(\+?[78][\s ]?(?:\(?\d{3,4}\)?[\s ]?)\d{2,3}[-\s ]?\d{2}[-\s ]?\d{2})/g

function linkify(s: string): string {
  s = s.replace(
    URL_RE,
    (url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`,
  )
  s = s.replace(PHONE_RE, (ph) => `<a href="tel:${ph.replace(/[\s ()-]/g, '')}">${ph}</a>`)
  return s
}

export function sanitizeAnswer(html: string): string {
  if (!html) return ''
  let out = escapeHtml(html)
  out = restoreAllowedTags(out)
  out = linkify(out)
  return out
}
