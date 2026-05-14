import { AVAILABLE_APPS } from './Sidebar'

export default function ConnectAppModal({ connectedApps, onConnect, onClose }) {
  const unconnected = AVAILABLE_APPS.filter(
    app => !connectedApps.find(c => c.id === app.id)
  )

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>

        <div className="modal-header">
          <h2>Connect an App</h2>
          <button className="icon-btn" onClick={onClose} title="Close">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <div className="modal-body">
          {unconnected.length === 0 ? (
            <div className="empty">
              <div className="empty-icon">✦</div>
              <h3>All apps connected</h3>
              <p>All available apps are already connected to your account.</p>
            </div>
          ) : (
            unconnected.map(app => (
              <div key={app.id} className="modal-app-row">
                <app.Icon />
                <div>
                  <div className="ttl">{app.label}</div>
                </div>
                <button
                  className="btn sm"
                  style={{ marginLeft: 'auto' }}
                  onClick={() => { onConnect(app); onClose() }}
                >
                  Connect
                </button>
              </div>
            ))
          )}
        </div>

      </div>
    </div>
  )
}