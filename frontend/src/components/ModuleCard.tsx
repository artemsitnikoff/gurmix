import { useNavigate } from 'react-router-dom'
import type { BotModule } from '@/modules'
import './ModuleCard.css'

type Props = {
  module: BotModule
}

/**
 * ModuleCard — expert card on the picker grid.
 * active: clickable → /m/:id. locked: muted + «Скоро» badge, not clickable.
 * Emoji sits in an accent-colored circle (var(--accent-color)).
 */
export function ModuleCard({ module }: Props) {
  const navigate = useNavigate()
  const locked = module.status === 'locked'

  function handleClick() {
    if (locked) return
    navigate(`/m/${module.id}`)
  }

  return (
    <div
      className={locked ? 'module-card locked' : 'module-card'}
      onClick={handleClick}
      role={locked ? undefined : 'button'}
      tabIndex={locked ? undefined : 0}
      onKeyDown={(e) => {
        if (!locked && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          handleClick()
        }
      }}
      style={{ '--accent-color': `var(${module.accent})` } as React.CSSProperties}
    >
      <div className="module-emoji">{module.emoji}</div>
      <div className="module-body">
        <div className="module-title">{module.title}</div>
        <div className="module-short">{module.short}</div>
      </div>
      {locked && <span className="module-badge">Скоро</span>}
    </div>
  )
}
