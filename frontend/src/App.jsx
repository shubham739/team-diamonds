import { useState, useEffect } from 'react'
import { userManager } from './auth/authConfig'

import AuthCallback from './auth/AuthCallback'
import JiraCallback from './auth/JiraCallback'
import Sidebar, { AVAILABLE_APPS } from './components/Sidebar'
import ConnectedApps from './pages/ConnectedApps'
import ConnectAppModal from './components/ConnectAppModal'
import Topbar from './components/Topbar'
import Home from './pages/Home'
import Issues from './pages/Issues'
import Commands from './pages/Commands'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

const PAGES = {
  overview:      Home,
  issues:        Issues,
  commands:      Commands,
  analytics:     Analytics,
  connectedApps: ConnectedApps,
  settings:      Settings,
}

export default function App() {
  const [page, setPage] = useState('overview')
  const [theme, setTheme] = useState('light')
  const [user, setUser] = useState(null)
  const [connectedApps, setConnectedApps] = useState([])
  const [showConnectModal, setShowConnectModal] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (window.location.pathname === '/callback') return
    userManager.getUser().then(u => setUser(u))
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    const connected = AVAILABLE_APPS.filter(app => localStorage.getItem(app.storageKey))
    setConnectedApps(connected)
  }, [])

  const handleAppConnected = () => {
    const connected = AVAILABLE_APPS.filter(app => localStorage.getItem(app.storageKey))
    setConnectedApps(connected)
  }

  if (window.location.pathname === '/callback') return <AuthCallback />
  if (window.location.pathname === '/jira/callback') return <JiraCallback onConnected={handleAppConnected} />
  if (!user) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        fontFamily: 'var(--font-sans)',
      }}>
        <div style={{
          background: 'var(--bg-elev)',
          border: '1px solid var(--line)',
          borderRadius: 'var(--r-3)',
          padding: '40px 36px',
          width: '100%',
          maxWidth: '360px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '24px',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <div className="brand-mark" style={{ width: 36, height: 36, borderRadius: 10 }} />
            <div style={{ textAlign: 'center' }}>
              <div className="brand-name" style={{ fontSize: 18 }}>Team Diamonds</div>
              <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 4 }}>
                Sign in to continue
              </div>
            </div>
          </div>
          <div style={{ width: '100%', height: 1, background: 'var(--line)' }} />
          <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              className="btn primary"
              style={{ width: '100%', justifyContent: 'center', height: 38, fontSize: 14 }}
              onClick={() => userManager.signinRedirect()}
            >
              Sign in
            </button>
            <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--ink-4)', margin: 0, lineHeight: 1.5 }}>
              Secure authentication via AWS Cognito
            </p>
          </div>
        </div>
      </div>
    )
  }

  const username = user?.profile?.email ?? user?.profile?.['cognito:username'] ?? user?.profile?.sub ?? null
  const Page = PAGES[page] ?? Home
  const sideW = collapsed ? 52 : 'var(--side-w)'

  console.log(user?.profile)

const handleConnect = async (app) => {
    try {
      // 1. Get the Cognito token from your user object
      // (Depending on your Cognito setup, this might be user.id_token instead)
      const token = user.id_token // cognito token

      if (!token) {
        throw new Error("No authentication token found");
      }

      // 2. Define your API Gateway URL
      const API_BASE_URL = import.meta.env.VITE_API_URL;

      console.log("before fetch")

      // 3. Make the POST request to the /oauth endpoint
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token // Passes the Cognito authorizer
        },
        body: JSON.stringify({
          action: 'get_auth_url',
          provider: app.id, // e.g., 'jira' or 'slack'
          // redirect_uri: `${window.location.origin}/jira/callback` // Return to frontend callback handler route
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      console.log("past fetch")

      const data = await response.json();

      console.log("past await response")

      // 4. Redirect to the third-party OAuth URL provided by your Lambda
      if (data.authUrl) {
        window.location.href = data.authUrl;
      } else {
        console.error("Lambda did not return an authUrl");
      }

    } catch (error) {
      console.error("Failed to initiate OAuth flow:", error);
    }
  }

  return (
    <div className="app">
      <Sidebar
        activePage={page}
        onNavigate={setPage}
        connectedApps={connectedApps}
        onConnectApp={() => setShowConnectModal(true)}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(c => !c)}
      />
      <div className="main" style={{ marginLeft: sideW, transition: 'margin-left 0.2s ease' }}>
      <Topbar
        page={page}
        theme={theme}
        onThemeToggle={() => setTheme(t => (t === 'light' ? 'dark' : 'light'))}
        username={username}
      />
        <div className="page">
          <Page onNavigate={setPage} idToken={user?.id_token} userEmail={user?.profile?.email} />
        </div>
      </div>
      {showConnectModal && (
        <ConnectAppModal
          connectedApps={connectedApps}
          onConnect={handleConnect}
          onClose={() => setShowConnectModal(false)}
        />
      )}
    </div>
  )
}