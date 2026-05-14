import { useState } from 'react'
import { ISSUES } from '../data/mock'
import { IcoRefresh, IcoPlus } from '../components/Icons'

const STATUS_MAP = {
  todo:        { cls: 'status-todo',      label: 'To Do'       },
  in_progress: { cls: 'status-progress',  label: 'In Progress' },
  complete:    { cls: 'status-complete',  label: 'Complete'    },
  cancelled:   { cls: 'status-cancelled', label: 'Cancelled'   },
}

function StatusPill({ status }) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.todo
  return <span className={`status-pill ${s.cls}`}>{s.label}</span>
}

function formatMembers(members) {
  if (!members || members.length === 0) return <span style={{ color: 'var(--ink-4)' }}>Unassigned</span>
  return members.map(m => m.split('@')[0]).join(', ')
}

const FILTERS = [
  { id: 'all',         label: 'All' },
  { id: 'todo',        label: 'To Do' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'complete',    label: 'Complete' },
  { id: 'cancelled',   label: 'Cancelled' },
]

export default function Issues() {
  const [filter, setFilter] = useState('all')
  const [selected, setSelected] = useState(null)

  const visible = filter === 'all' ? ISSUES : ISSUES.filter(i => i.status === filter)

  const selectedIssue = ISSUES.find(i => i.id === selected)

  return (
    <>
      <div className="page-h">
        <div>
          <h1 className="page-title">Issues</h1>
          <p className="page-sub">
            {ISSUES.length} issues across {[...new Set(ISSUES.map(i => i.id.split('-')[0]))].join(', ')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn"><IcoRefresh /> Sync from Jira</button>
          <button className="btn primary"><IcoPlus /> Create issue</button>
        </div>
      </div>

      {/* Filter row */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button
            key={f.id}
            className={`btn sm${filter === f.id ? '' : ' ghost'}`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
            <span style={{ marginLeft: 4, fontSize: 11, color: filter === f.id ? 'inherit' : 'var(--ink-4)' }}>
              {f.id === 'all' ? ISSUES.length : ISSUES.filter(i => i.status === f.id).length}
            </span>
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 380px' : '1fr', gap: 14 }}>
        {/* Table */}
        <div className="card">
          <div className="iss-h">
            <span>ID</span>
            <span>Title</span>
            <span>Status</span>
            <span>Members</span>
            <span>Due</span>
            <span></span>
          </div>
          {visible.length === 0 ? (
            <div className="iss-empty">No issues match this filter.</div>
          ) : visible.map(issue => (
            <div
              key={issue.id}
              className="iss-r"
              style={selected === issue.id ? { background: 'var(--accent-soft)' } : {}}
            >
              <span className="iss-id">{issue.id}</span>
              <span className="iss-title">{issue.title}</span>
              <StatusPill status={issue.status} />
              <span style={{ fontSize: 12.5, color: 'var(--ink-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {formatMembers(issue.members)}
              </span>
              <span className="mono" style={{ fontSize: 12, color: issue.due_date ? 'var(--ink-3)' : 'var(--ink-4)' }}>
                {issue.due_date ?? '—'}
              </span>
              <span style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  className="btn sm ghost"
                  onClick={() => setSelected(selected === issue.id ? null : issue.id)}
                >
                  {selected === issue.id ? 'Close' : 'View'}
                </button>
              </span>
            </div>
          ))}
        </div>

        {/* Detail panel */}
        {selectedIssue && (
          <div className="card" style={{ padding: 20, alignSelf: 'start', position: 'sticky', top: 68 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <span className="iss-id" style={{ fontSize: 13 }}>{selectedIssue.id}</span>
              <button className="btn sm ghost" onClick={() => setSelected(null)}>✕</button>
            </div>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12, lineHeight: 1.35 }}>{selectedIssue.title}</div>

            <dl style={{ margin: 0, display: 'grid', gap: 10 }}>
              {[
                { k: 'Status',  v: <StatusPill status={selectedIssue.status} /> },
                { k: 'Members', v: selectedIssue.members?.length ? selectedIssue.members.join(', ') : '—' },
                { k: 'Due',     v: selectedIssue.due_date ?? '—' },
              ].map(r => (
                <div key={r.k} style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: 8, fontSize: 13 }}>
                  <dt style={{ color: 'var(--ink-3)' }}>{r.k}</dt>
                  <dd style={{ margin: 0 }}>{r.v}</dd>
                </div>
              ))}
            </dl>

            {selectedIssue.desc && (
              <div style={{ marginTop: 16, borderTop: '1px solid var(--line)', paddingTop: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--ink-4)', marginBottom: 8 }}>Description</div>
                <p style={{ fontSize: 13, color: 'var(--ink-2)', margin: 0, lineHeight: 1.6 }}>{selectedIssue.desc}</p>
              </div>
            )}

            <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
              <button className="btn sm primary">Edit</button>
              <button className="btn sm danger">Delete</button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
