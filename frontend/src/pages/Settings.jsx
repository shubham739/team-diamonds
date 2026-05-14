import { useState } from 'react'
import { SESSION, JIRA_CONNECTION, OR_BILLING, MODEL_BREAKDOWN } from '../data/mock'
import { IcoArr } from '../components/Icons'
import { getApiUrl } from '../config/api'
import { userManager } from '../auth/authConfig'

export default function Settings() {
  const [jiraConnected, setJiraConnected] = useState(JIRA_CONNECTION.connected)
  const [pingResult, setPingResult] = useState(null)

  const handlePing = () => {
    setPingResult('checking…')
    fetch(getApiUrl('/health'))
      .then(r => r.json())
      .then(d => setPingResult(d.status === 'ok' ? '✓ Service healthy' : '✗ Unexpected response'))
      .catch(() => setPingResult('✗ Service unreachable'))
  }

  return (
    <>
      <div className="page-h">
        <div>
          <h1 className="page-title">Settings</h1>
        </div>
      </div>

      <div className="settings-section">

        {/* Session */}
        <div className="section">
          <div className="section-h"><h2>Session</h2></div>
          <div className="card settings-card">
            <div className="settings-row">
              <div>
                <div className="settings-label">Signed in as</div>
                <div className="settings-desc">{SESSION.email}</div>
              </div>
              <div className="ava">{SESSION.name.slice(0, 1)}</div>
            </div>
            <div className="settings-row">
              <div>
                <div className="settings-label">Account ID</div>
                <div className="settings-desc">Atlassian account identifier</div>
              </div>
              <span className="mono" style={{ fontSize: 12, color: 'var(--ink-3)' }}>{SESSION.user_id}</span>
            </div>
            <div className="settings-row">
              <div>
                <div className="settings-label">Token storage</div>
                <div className="settings-desc">In-memory only — cleared on server restart</div>
              </div>
              <span style={{ fontSize: 12, color: 'var(--warn)' }}>In-memory</span>
            </div>
          </div>
        </div>

        {/* Jira */}
        <div className="section">
          <div className="section-h"><h2>Jira Authentication</h2></div>
          <div className="card settings-card">
            <div className="settings-row">
              <div>
                <div className="settings-label">Jira Cloud site</div>
                <div className="settings-desc">OAuth 2.0 Authorization Code flow</div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className={`ig-status${jiraConnected ? '' : ' off'}`} style={{ marginLeft: 0 }}>
                  <span className="d" />{jiraConnected ? 'Connected' : 'Not connected'}
                </span>
                {jiraConnected ? (
                  <button className="btn sm danger" onClick={() => setJiraConnected(false)}>Disconnect</button>
                ) : (
                  <button className="btn sm primary" onClick={async () => {
                    const user = await userManager.getUser()
                    const cognitoSub = user?.profile?.sub ?? ''
                    window.location.href = getApiUrl('/auth/login') + (cognitoSub ? `?cognito_sub=${encodeURIComponent(cognitoSub)}` : '')
                  }}>
                    Connect <IcoArr />
                  </button>
                )}
              </div>
            </div>
            {jiraConnected && (
              <>
                <div className="settings-row">
                  <div>
                    <div className="settings-label">Site</div>
                    <div className="settings-desc">Atlassian cloud instance</div>
                  </div>
                  <span className="mono" style={{ fontSize: 12, color: 'var(--ink-2)' }}>{JIRA_CONNECTION.site}</span>
                </div>
                <div className="settings-row">
                  <div>
                    <div className="settings-label">Projects</div>
                    <div className="settings-desc">Accessible via API</div>
                  </div>
                  <span style={{ fontSize: 12.5, color: 'var(--ink-2)' }}>{JIRA_CONNECTION.projects.join(', ')}</span>
                </div>
                <div className="settings-row">
                  <div>
                    <div className="settings-label">OAuth scope</div>
                    <div className="settings-desc">Permissions granted during auth flow</div>
                  </div>
                  <span className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>{JIRA_CONNECTION.scope}</span>
                </div>
              </>
            )}
            <div className="settings-row">
              <div>
                <div className="settings-label">OAuth redirect URI</div>
                <div className="settings-desc">Must match your Atlassian app configuration</div>
              </div>
              <span className="mono" style={{ fontSize: 12, color: 'var(--ink-3)' }}>localhost:8000/auth/callback</span>
            </div>
          </div>
        </div>

        {/* API service */}
        <div className="section">
          <div className="section-h"><h2>Jira Service API</h2></div>
          <div className="card settings-card">
            <div className="settings-row">
              <div>
                <div className="settings-label">Base URL</div>
                <div className="settings-desc">FastAPI backend — all /issues and /chat endpoints</div>
              </div>
              <span className="mono" style={{ fontSize: 12, color: 'var(--ink-2)' }}>localhost:8000</span>
            </div>
            <div className="settings-row">
              <div>
                <div className="settings-label">Health check</div>
                <div className="settings-desc">GET /health · no auth required</div>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {pingResult && (
                  <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: pingResult.startsWith('✓') ? 'var(--ok)' : 'var(--bad)' }}>
                    {pingResult}
                  </span>
                )}
                <button className="btn sm" onClick={handlePing}>Ping</button>
              </div>
            </div>
            <div className="settings-row">
              <div>
                <div className="settings-label">Swagger UI</div>
                <div className="settings-desc">Interactive API docs</div>
              </div>
              <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="btn sm ghost">
                Open ↗
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
