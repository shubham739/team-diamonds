import { IcoSearch, IcoBell, IcoHelp } from './Icons'
import { signOutRedirect } from '../auth/authConfig'


const PAGE_LABELS = {
  overview:      'Overview',
  issues:        'Issues',
  commands:      'AI Commands',
  analytics:     'Analytics',
  connectedApps: 'Connected Apps',
  settings:      'Settings',
}

export default function Topbar({ page, theme, onThemeToggle, username }) {
  return (
    <div className="topbar">
      <div className="crumbs">
        <span>Team Diamonds</span>
        <span className="crumb-sep">/</span>
        <b>{PAGE_LABELS[page] ?? page}</b>
      </div>

      <div className="topbar-spacer" />

      {username && (
        <span style={{ fontSize: 13, color: 'var(--ink-3)', whiteSpace: 'nowrap' }}>
          Hello, <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{username}</span>
        </span>
      )}

      <button
        className="btn"
        style={{ color: '#C26E4F', borderColor: '#C26E4F', whiteSpace: 'nowrap' }}
        title="Sign Out"
        onClick={signOutRedirect}
      >
        Sign Out
      </button>
    </div>
  )
}