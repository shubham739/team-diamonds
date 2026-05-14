import { useState } from 'react'
import { CHAT_HISTORY, COMMAND_EXAMPLES } from '../data/mock'
import { IcoArr } from '../components/Icons'

const STATUS_MAP = {
  todo:        { cls: 'status-todo',      label: 'To Do'       },
  in_progress: { cls: 'status-progress',  label: 'In Progress' },
  complete:    { cls: 'status-complete',  label: 'Complete'    },
  cancelled:   { cls: 'status-cancelled', label: 'Cancelled'   },
}

function ToolCallRow({ action }) {
  const resultIsError = action.result?.error
  const resultIsDeleted = action.result?.status === 'deleted'
  const resultIsIssue = action.result?.id && !resultIsDeleted

  return (
    <div style={{
      padding: '8px 12px',
      background: 'var(--bg-sunken)',
      borderRadius: 6,
      fontSize: 12,
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>{action.tool}</span>
        {Object.entries(action.args).map(([k, v]) => (
          <span key={k} style={{ color: 'var(--ink-3)' }}>
            <span style={{ color: 'var(--ink-4)' }}>{k}=</span>
            <span className="mono">{JSON.stringify(v)}</span>
          </span>
        ))}
      </div>
      {resultIsError && (
        <div style={{ color: 'var(--bad)', fontFamily: 'var(--font-mono)' }}>↳ {action.result.error}</div>
      )}
      {resultIsIssue && (
        <div style={{ color: 'var(--ok)', fontFamily: 'var(--font-mono)' }}>
          ↳ {action.result.id} · {action.result.title?.slice(0, 48)}{action.result.title?.length > 48 ? '…' : ''} · {action.result.status}
        </div>
      )}
      {resultIsDeleted && (
        <div style={{ color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>↳ {action.result.issue_id} deleted</div>
      )}
      {Array.isArray(action.result) && (
        <div style={{ color: 'var(--ink-3)', fontFamily: 'var(--font-mono)' }}>
          ↳ {action.result.length} issue{action.result.length !== 1 ? 's' : ''} returned
        </div>
      )}
    </div>
  )
}

function CommandCard({ cmd }) {
  const [expanded, setExpanded] = useState(false)
  const statusCls = cmd.status === 'ok' ? 'ok' : cmd.status === 'running' ? 'run' : 'fail'
  const statusLabel = cmd.status === 'ok' ? 'success' : cmd.status === 'running' ? 'running' : 'failed'

  return (
    <div style={{ borderTop: '1px solid var(--line)', padding: '14px 20px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 12, alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 13, color: 'var(--ink)', marginBottom: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {cmd.message}
          </div>
          {cmd.reply && !expanded && (
            <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 4 }}>
              {cmd.reply.slice(0, 100)}{cmd.reply.length > 100 ? '…' : ''}
            </div>
          )}
          {cmd.actions.length > 0 && (
            <button
              className="btn sm ghost"
              style={{ marginTop: 8, fontSize: 11 }}
              onClick={() => setExpanded(e => !e)}
            >
              {expanded ? '▲ Hide' : `▼ ${cmd.actions.length} tool call${cmd.actions.length > 1 ? 's' : ''}`}
            </button>
          )}
          {expanded && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {cmd.actions.map((a, i) => <ToolCallRow key={i} action={a} />)}
              {cmd.reply && (
                <div style={{ padding: '8px 12px', background: 'color-mix(in oklab, var(--ok) 8%, transparent)', borderRadius: 6, fontSize: 12.5, color: 'var(--ink-2)', lineHeight: 1.5 }}>
                  <span style={{ color: 'var(--ok)', fontWeight: 600, marginRight: 6 }}>↳ Reply</span>{cmd.reply}
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{ textAlign: 'right', flex: 'none' }}>
          <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--ink-3)' }}>{cmd.ts}</div>
          {cmd.latency_ms && (
            <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--ink-4)', marginTop: 2 }}>{cmd.latency_ms}ms</div>
          )}
        </div>

        <span className={`rc-st ${statusCls}`} style={{ flex: 'none', alignSelf: 'flex-start' }}>
          <span className="d" />{statusLabel}
        </span>
      </div>
    </div>
  )
}

export default function Commands() {
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || running) return
    setRunning(true)
    // Will POST to /api/chat when wired up
    setTimeout(() => { setRunning(false); setInput('') }, 1500)
  }

  return (
    <>
      <div className="page-h">
        <div>
          <h1 className="page-title">AI Commands</h1>
          <p className="page-sub">Send natural language instructions to your Jira workspace via OpenRouter.</p>
        </div>
      </div>

      {/* Input */}
      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder='e.g. "create issue fix login bug in ENG" or "list my open P0 tickets"'
              style={{
                flex: 1, height: 42, padding: '0 14px',
                border: '1px solid var(--line)', borderRadius: 8,
                background: 'var(--bg-sunken)', color: 'var(--ink)',
                font: 'inherit', fontSize: 13, outline: 'none',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
              onBlur={e => (e.target.style.borderColor = 'var(--line)')}
            />
            <button type="submit" className="btn primary" style={{ height: 42 }} disabled={!input.trim() || running}>
              {running ? 'Running…' : <><IcoArr /> Send</>}
            </button>
          </div>
        </form>

        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 11, color: 'var(--ink-4)', marginBottom: 8, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Examples
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {COMMAND_EXAMPLES.map((ex, i) => (
              <button
                key={i}
                className="btn sm ghost"
                onClick={() => setInput(ex)}
                style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* History */}
      <div className="section">
        <div className="section-h">
          <h2>Command history</h2>
          <span className="meta">{CHAT_HISTORY.length} commands · click tool calls to expand</span>
        </div>
        <div className="card">
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto auto',
            gap: 12, padding: '10px 20px',
            borderBottom: '1px solid var(--line)',
            fontSize: 11, fontWeight: 600, letterSpacing: '0.06em',
            textTransform: 'uppercase', color: 'var(--ink-3)',
          }}>
            <span>Command · Reply</span>
            <span>Time</span>
            <span>Status</span>
          </div>
          {CHAT_HISTORY.map(cmd => <CommandCard key={cmd.id} cmd={cmd} />)}
        </div>
      </div>
    </>
  )
}
