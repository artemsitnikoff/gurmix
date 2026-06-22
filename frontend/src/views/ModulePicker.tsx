import { useMemo } from 'react'
import { MODULES } from '@/modules'
import { ModuleCard } from '@/components/ModuleCard'
import { APP_VERSION } from '@/version'
import './ModulePicker.css'

/**
 * ModulePicker — main chat entry (`/`). Grid of 8 expert cards sorted by
 * order; active cards link into the module chat, locked show «Скоро».
 */
export default function ModulePicker() {
  const modules = useMemo(() => [...MODULES].sort((a, b) => a.order - b.order), [])

  return (
    <div className="picker">
      <header className="picker-header">
        <div className="picker-brand">
          <span className="picker-emoji">👨‍🍳</span>
          <span className="picker-brand-text">Нейро-шеф Гурмикс</span>
        </div>
        <span className="picker-version">v{APP_VERSION}</span>
      </header>

      <div className="picker-scroll">
        <div className="picker-inner">
          <h1 className="picker-title">Выберите эксперта</h1>
          <p className="picker-sub">
            8 модулей-экспертов по продуктам, технологиям и поставкам Гурмикс.
          </p>
          <div className="picker-grid">
            {modules.map((m) => (
              <ModuleCard key={m.id} module={m} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
