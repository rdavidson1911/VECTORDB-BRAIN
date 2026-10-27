import { NAV } from '../branding'

export type AppTab = keyof typeof NAV

export type AppNavProps = {
  active: AppTab
  onChange: (tab: AppTab) => void
}

const TABS: AppTab[] = ['query', 'ingest', 'corpus', 'analytics']

export function AppNav({ active, onChange }: AppNavProps) {
  return (
    <nav className="app-nav" aria-label="Primary">
      {TABS.map((tab) => (
        <button
          key={tab}
          type="button"
          className={active === tab ? 'app-nav__tab is-active' : 'app-nav__tab'}
          aria-current={active === tab ? 'page' : undefined}
          onClick={() => onChange(tab)}
        >
          {NAV[tab]}
        </button>
      ))}
    </nav>
  )
}
