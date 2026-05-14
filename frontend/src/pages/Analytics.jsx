import { useState, useEffect } from 'react'
import { IcoRefresh } from '../components/Icons'

const STATUS_CONFIG = {
  todo:        { label: 'To Do',       color: 'var(--ink-3)'  },
  in_progress: { label: 'In Progress', color: 'var(--accent)' },
  complete:    { label: 'Complete',    color: 'var(--ok)'     },
  cancelled:   { label: 'Cancelled',   color: 'var(--bad)'    },
}

function normalizeStatus(status) {
  return String(status || '').trim().toLowerCase().replace(/^status\./, '')
}

function isThisWeek(dateStr) {
  if (!dateStr) return false
  const date = new Date(dateStr)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const endOfWeek = new Date(startOfToday.getTime() + 7 * 24 * 60 * 60 * 1000)
  return date >= startOfToday && date < endOfWeek
}

function IssueRow({ issue }) {
  const status = normalizeStatus(issue.status)
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: 'var(--ink-3)' }
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '80px 1fr 90px',
      gap: 10,
      padding: '9px 20px',
      borderTop: '1px solid var(--line)',
      alignItems: 'center',
      fontSize: 13,
    }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent)' }}>{issue.id}</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--ink)' }}>{issue.title}</span>
      <span style={{ fontSize: 11, color: cfg.color, fontWeight: 500 }}>{cfg.label}</span>
    </div>
  )
}

function IssueList({ issues, loading, emptyText }) {
  if (loading) {
    return <div style={{ padding: '20px', fontSize: 13, color: 'var(--ink-4)' }}>Loading…</div>
  }
  if (!issues.length) {
    return <div style={{ padding: '20px', fontSize: 13, color: 'var(--ink-4)' }}>{emptyText}</div>
  }
  return (
    <div style={{ maxHeight: 280, overflowY: 'auto' }}>
      {issues.map(i => <IssueRow key={i.id} issue={i} />)}
    </div>
  )
}

export default function Analytics({ userEmail, onNavigate }) {
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const jiraConnected = !!localStorage.getItem('jira_access_token')

  if (!jiraConnected) {
    return (
      <>
        <div className="page-h">
          <div>
            <h1 className="page-title">Analytics</h1>
            <p className="page-sub">Overview of your Jira workspace</p>
          </div>
        </div>
        <div className="card">
          <div className="empty">
            <h3>Connect your Jira account to see analytics about your tasks</h3>
            <p>Link your Jira workspace to view task counts, upcoming due dates, and assignments.</p>
            <button className="btn primary" onClick={() => onNavigate?.('connectedApps')}>
              Connect Jira
            </button>
          </div>
        </div>
      </>
    )
  }

  const fetchIssues = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('jira_access_token') || 'anon-token'
      const res = await fetch('/api/issues?max_results=100', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`Failed to fetch issues (${res.status})`)
      const data = await res.json()
      setIssues(data.issues || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchIssues() }, [])

  const statusCounts = { todo: 0, in_progress: 0, complete: 0, cancelled: 0 }
  issues.forEach(issue => {
    const s = normalizeStatus(issue.status)
    if (s in statusCounts) statusCounts[s]++
  })

  const dueThisWeek = issues.filter(i => isThisWeek(i.due_date))
  const assignedToMe = userEmail
    ? issues.filter(i => Array.isArray(i.members) && i.members.some(m => m.toLowerCase() === userEmail.toLowerCase()))
    : []

  return (
    <>
      <div className="page-h">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-sub">Overview of your Jira workspace</p>
        </div>
        <button className="btn" onClick={fetchIssues} disabled={loading}>
          <IcoRefresh /> {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'var(--bad)', marginBottom: 16, fontSize: 13, padding: '10px 14px', background: 'color-mix(in oklab, var(--bad) 8%, transparent)', borderRadius: 8 }}>
          {error}
        </div>
      )}

      {/* Status breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
          <div key={key} className="card" style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-4)', marginBottom: 8 }}>
              {cfg.label}
            </div>
            <div style={{ fontSize: 36, fontWeight: 700, color: cfg.color, lineHeight: 1 }}>
              {loading ? '—' : statusCounts[key]}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Due this week */}
        <div className="card">
          <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Due This Week</span>
            <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>{loading ? '—' : `${dueThisWeek.length} tasks`}</span>
          </div>
          <IssueList issues={dueThisWeek} loading={loading} emptyText="No tasks due this week" />
        </div>

        {/* Assigned to me */}
        <div className="card">
          <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Assigned to Me</span>
            <span style={{ fontSize: 12, color: 'var(--ink-4)' }}>{loading ? '—' : `${assignedToMe.length} tasks`}</span>
          </div>
          {!userEmail
            ? <div style={{ padding: '20px', fontSize: 13, color: 'var(--ink-4)' }}>No email found — set VITE_TEST_EMAIL or sign in via Cognito.</div>
            : <IssueList issues={assignedToMe} loading={loading} emptyText="No tasks assigned to you" />
          }
        </div>
      </div>
    </>
  )
}
