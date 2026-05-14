import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { IcoPlus } from '../components/Icons'
import { getApiUrl } from '../config/api'

const STATUS_LABELS = {
  todo: 'To Do',
  in_progress: 'In Progress',
  complete: 'Complete',
  cancelled: 'Cancelled',
}

const STATUS_SORT_ORDER = {
  todo: 0,
  in_progress: 1,
  cancelled: 2,
  complete: 3,
}

function normalizeIssueStatus(status) {
  return String(status || '')
    .trim()
    .toLowerCase()
    .replace(/^status\./, '')
}

function formatIssueStatus(status) {
  if (!status) return 'Unknown'
  const normalized = normalizeIssueStatus(status)
  return STATUS_LABELS[normalized] || normalized.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function sortRetrievedIssues(issues) {
  return [...issues].sort((left, right) => {
    const leftTime = left.due_date ? Date.parse(left.due_date) : Number.NaN
    const rightTime = right.due_date ? Date.parse(right.due_date) : Number.NaN
    const leftHasDate = Number.isFinite(leftTime)
    const rightHasDate = Number.isFinite(rightTime)

    if (leftHasDate && rightHasDate && leftTime !== rightTime) {
      return leftTime - rightTime
    }
    if (leftHasDate !== rightHasDate) {
      return leftHasDate ? -1 : 1
    }

    const leftStatusOrder = STATUS_SORT_ORDER[normalizeIssueStatus(left.status)] ?? Number.MAX_SAFE_INTEGER
    const rightStatusOrder = STATUS_SORT_ORDER[normalizeIssueStatus(right.status)] ?? Number.MAX_SAFE_INTEGER
    if (leftStatusOrder !== rightStatusOrder) {
      return leftStatusOrder - rightStatusOrder
    }

    return String(left.title || '').localeCompare(String(right.title || ''))
  })
}

async function parseResponseBody(response) {
  const raw = await response.text()
  if (!raw) {
    return {}
  }
  try {
    return JSON.parse(raw)
  } catch {
    return { detail: raw }
  }
}

export default function Home({ onNavigate }) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [issues, setIssues] = useState([])
  const [isSending, setIsSending] = useState(false)
  const [showCreateIssueModal, setShowCreateIssueModal] = useState(false)
  const [createIssueText, setCreateIssueText] = useState('')
  const [isCreatingIssue, setIsCreatingIssue] = useState(false)
  const [createIssueFeedback, setCreateIssueFeedback] = useState('')
  const sortedIssues = sortRetrievedIssues(issues)

  const getAuthHeaders = () => {
    const jiraAccessToken = localStorage.getItem('jira_access_token')
    const authToken = jiraAccessToken || 'chat-anon-token'
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    }
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isSending) return

    const pendingMessageId = `assistant-pending-${Date.now()}`

    setMessages(prev => [
      ...prev,
      { role: 'user', text },
      { id: pendingMessageId, role: 'assistant', text: 'Thinking ...', pending: true },
    ])
    setInput('')

    try {
      setIsSending(true)
      const response = await fetch(getApiUrl('/chat-relay'), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: text }),
      })

      const data = await parseResponseBody(response)
      if (!response.ok) {
        throw new Error(data.detail || `Chat request failed (${response.status})`)
      }

      const nextIssues = data.actions
        ?.find(action => action.tool === 'list_issues' && Array.isArray(action.result))
        ?.result

      if (Array.isArray(nextIssues)) {
        setIssues(nextIssues)
      }

      setMessages(prev => prev.map(message => {
        if (message.id === pendingMessageId) {
          return { ...message, text: data.reply || 'Done.', pending: false }
        }
        return message
      }))
    } catch (error) {
      const fallbackMessage = error instanceof Error ? error.message : 'Unexpected error contacting the Jira AI service'
      setMessages(prev => prev.map(message => {
        if (message.id === pendingMessageId) {
          return { ...message, text: fallbackMessage, pending: false }
        }
        return message
      }))
    } finally {
      setIsSending(false)
    }
  }

  const handleCreateIssue = async () => {
    const issuePrompt = createIssueText.trim()
    if (!issuePrompt || isCreatingIssue) return

    setCreateIssueFeedback('')
    try {
      setIsCreatingIssue(true)
      const response = await fetch(getApiUrl('/chat-relay'), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message: `@jira Create a Jira issue from this request and confirm what was created: ${issuePrompt}`,
        }),
      })

      const data = await parseResponseBody(response)
      if (!response.ok) {
        throw new Error(data.detail || `Issue creation request failed (${response.status})`)
      }

      const createdIssue = data.actions?.find(action => action.tool === 'create_issue' && action.result?.id)?.result
      if (createdIssue) {
        setIssues(prev => [createdIssue, ...prev.filter(issue => issue.id !== createdIssue.id)])
        setCreateIssueFeedback(`Created ${createdIssue.id}: ${createdIssue.title}`)
      } else {
        setCreateIssueFeedback(data.reply || 'Request completed, but no created issue was returned.')
      }

      setMessages(prev => [...prev, { role: 'assistant', text: data.reply || 'Issue creation completed.' }])
      setCreateIssueText('')
      setShowCreateIssueModal(false)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unexpected error while creating issue'
      setCreateIssueFeedback(message)
    } finally {
      setIsCreatingIssue(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  return (
    <>
      {/* ── Header ── */}
      <div className="page-h">
        <div>
          <h1 className="page-title">Home</h1>
          <p className="page-sub">Chat with an AI Agent About Your Tasks</p>
        </div>
        <button className="btn primary" onClick={() => setShowCreateIssueModal(true)}>
          <IcoPlus /> New issue
        </button>
      </div>

      {showCreateIssueModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(10, 15, 25, 0.44)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 50,
            padding: 16,
          }}
          onClick={() => {
            if (!isCreatingIssue) {
              setShowCreateIssueModal(false)
            }
          }}
        >
          <div
            className="card"
            onClick={event => event.stopPropagation()}
            style={{
              width: 'min(760px, 100%)',
              padding: 18,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div>
              <h2 style={{ margin: 0, fontSize: 18, color: 'var(--ink)' }}>Create Jira Issue</h2>
              <p style={{ margin: '6px 0 0 0', color: 'var(--ink-3)', fontSize: 13 }}>
                Describe the issue details. Include title, due date, assignee, and description in plain language.
              </p>
            </div>
            <textarea
              value={createIssueText}
              onChange={event => setCreateIssueText(event.target.value)}
              placeholder="Example: Create an issue titled 'Finalize launch checklist', due 2026-05-18, assign to alice@example.com, description: prepare release sign-off notes and QA handoff."
              rows={7}
              style={{
                width: '100%',
                resize: 'vertical',
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: '10px 12px',
                fontSize: 13,
                fontFamily: 'var(--font-sans)',
                background: 'var(--bg-sunken)',
                color: 'var(--ink)',
                outline: 'none',
                lineHeight: 1.5,
                minHeight: 140,
              }}
            />
            {createIssueFeedback && (
              <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{createIssueFeedback}</div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                className="btn ghost"
                onClick={() => setShowCreateIssueModal(false)}
                disabled={isCreatingIssue}
              >
                Cancel
              </button>
              <button
                className="btn primary"
                onClick={handleCreateIssue}
                disabled={!createIssueText.trim() || isCreatingIssue}
              >
                {isCreatingIssue ? 'Creating…' : 'Create issue'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Three-zone panel ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'stretch', flexWrap: 'wrap' }}>
          {/* Zone 2 — Chat messages */}
          <div className="card" style={{ minHeight: 260, display: 'flex', flexDirection: 'column', flex: '1 1 520px' }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-4)', padding: '14px 20px 10px', borderBottom: '1px solid var(--line)' }}>
              Conversation
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              {messages.length === 0 ? (
                <div style={{ margin: 'auto', textAlign: 'center', color: 'var(--ink-4)', fontSize: 13 }}>
                  Ask the AI agent anything about your Jira workspace
                </div>
              ) : (
                messages.map((m, i) => (
                  <div key={m.id || i} style={{
                    display: 'flex',
                    justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                  }}>
                    <div style={{
                      maxWidth: '72%',
                      padding: '8px 12px',
                      borderRadius: m.role === 'user' ? '10px 10px 2px 10px' : '10px 10px 10px 2px',
                      background: m.role === 'user' ? 'var(--ink)' : 'var(--bg-sunken)',
                      color: m.role === 'user' ? 'var(--bg)' : 'var(--ink)',
                      fontSize: 13,
                      lineHeight: 1.5,
                      opacity: m.pending ? 0.8 : 1,
                      fontStyle: m.pending ? 'italic' : 'normal',
                    }}>
                      {m.role === 'assistant' && !m.pending ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => <p style={{ margin: '0 0 8px 0' }}>{children}</p>,
                            ul: ({ children }) => <ul style={{ margin: '0 0 8px 18px', padding: 0 }}>{children}</ul>,
                            ol: ({ children }) => <ol style={{ margin: '0 0 8px 18px', padding: 0 }}>{children}</ol>,
                            li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
                            code: ({ children }) => (
                              <code
                                style={{
                                  fontFamily: 'var(--font-mono)',
                                  background: 'color-mix(in oklab, var(--ink) 8%, transparent)',
                                  borderRadius: 4,
                                  padding: '1px 4px',
                                }}
                              >
                                {children}
                              </code>
                            ),
                          }}
                        >
                          {m.text}
                        </ReactMarkdown>
                      ) : (
                        m.text
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Zone 1 — Jira issues */}
          <div className="card" style={{ padding: '16px 20px', flex: '0 1 360px', minWidth: 280 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-4)', marginBottom: 12 }}>
              Retrieved issues
            </div>
            {sortedIssues.length === 0 ? (
              <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--ink-4)', fontSize: 13 }}>
                Issues retrieved from Jira will appear here
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '96px 1fr 86px',
                    gap: 10,
                    padding: '0 0 8px 0',
                    borderBottom: '1px solid var(--line)',
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    color: 'var(--ink-4)',
                  }}
                >
                  <span>Due Date</span>
                  <span>Title</span>
                  <span>Status</span>
                </div>
                {sortedIssues.map(issue => (
                  <div
                    key={issue.id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '96px 1fr 86px',
                      gap: 10,
                      alignItems: 'center',
                      padding: '8px 0',
                      borderTop: '1px solid var(--line)',
                      fontSize: 13,
                    }}
                  >
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent)' }}>{issue.due_date || 'No due date'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{issue.title}</span>
                    <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>{formatIssueStatus(issue.status)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Zone 3 — Input */}
        <div className="card" style={{ padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the AI agent… If you have a question for Jira, query it with @jira. (Enter to send, Shift+Enter for new line)"
            rows={3}
            style={{
              flex: 1,
              resize: 'none',
              border: '1px solid var(--line)',
              borderRadius: 8,
              padding: '10px 12px',
              fontSize: 13,
              fontFamily: 'var(--font-sans)',
              background: 'var(--bg-sunken)',
              color: 'var(--ink)',
              outline: 'none',
              lineHeight: 1.5,
            }}
          />
          <button
            className="btn primary"
            style={{ height: 38, flexShrink: 0 }}
            onClick={handleSend}
            disabled={!input.trim() || isSending}
          >
            Send
          </button>
        </div>

      </div>
    </>
  )
}
