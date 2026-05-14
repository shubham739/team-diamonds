import { useState } from 'react'
import { IcoArr } from '../components/Icons'
import { getApiUrl } from '../config/api'
import { userManager } from '../auth/authConfig'

export default function ConnectedApps() {
  const [jiraConnected, setJiraConnected] = useState(!!localStorage.getItem('jira_access_token'))

  async function handleJiraConnect() {
    const user = await userManager.getUser()
    const cognitoSub = user?.profile?.sub ?? ''
    const loginUrl = getApiUrl('/auth/login') + (cognitoSub ? `?cognito_sub=${encodeURIComponent(cognitoSub)}` : '')
    window.location.href = loginUrl
  }

  async function handleJiraDisconnect() {
    const userId = localStorage.getItem('jira_user_id')
    try {
      await fetch(getApiUrl('/auth/logout') + (userId ? `?user_id=${encodeURIComponent(userId)}` : ''))
    } catch {
      // Ignore network errors — clear local state regardless
    }
    localStorage.removeItem('jira_access_token')
    localStorage.removeItem('jira_user_id')
    setJiraConnected(false)
  }

  return (
    <>
      <div className="page-h">
        <div>
          <h1 className="page-title">Connected Apps</h1>
          <p className="page-sub">Manage your connected services and integrations.</p>
        </div>
      </div>

      <section className="section">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-elev)', border: '1px solid var(--line)', borderRadius: 'var(--r-2)' }}>
            <span style={{ fontWeight: 500 }}>Jira Cloud</span>
            {jiraConnected ? (
              <button className="btn sm" onClick={handleJiraDisconnect}>Disconnect</button>
            ) : (
              <button className="btn sm primary" onClick={handleJiraConnect}>
                Authenticate <IcoArr />
              </button>
            )}
          </div>
        </div>
      </section>
    </>
  )
}