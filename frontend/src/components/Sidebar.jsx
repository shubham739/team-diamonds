import { useState } from 'react'
import { IcoOverview, IcoBox, IcoHomeChat, IcoIssues, IcoCommands, IcoChart, IcoSettings, IcoIssueTracker, IcoChat } from './Icons'

const NAV = [
  { id: 'overview',      label: 'Overview',       Icon: IcoHomeChat     },
  { id: 'analytics',    label: 'Analytics',      Icon: IcoChart        },
  { id: 'connectedApps', label: 'Connected Apps', Icon: IcoIssueTracker },
]

const NAV_2 = [
  { id: 'settings', label: 'Settings', Icon: IcoSettings },
]

export const AVAILABLE_APPS = [
  {
    id: 'jira',
    label: 'Jira',
    Icon: IcoIssueTracker,
    storageKey: 'jira_access_token',
  },
  {
    id: 'slack',
    label: 'Slack',
    Icon: IcoChat,
    storageKey: 'slack_access_token',
  },
]

function NavItem({ item, active, onClick, collapsed }) {
  return (
    <div
      className={`nav-item${active ? ' active' : ''}`}
      onClick={() => onClick(item.id)}
      title={collapsed ? item.label : undefined}
      style={{ justifyContent: collapsed ? 'center' : undefined }}
    >
      <item.Icon />
      {!collapsed && <span>{item.label}</span>}
      {!collapsed && item.dot && <span className="dot" />}
    </div>
  )
}

export default function Sidebar({ activePage, onNavigate, connectedApps, onConnectApp, collapsed, onToggleCollapse }) {
  return (
    <aside className="side" style={{ width: collapsed ? 52 : 'var(--side-w)', transition: 'width 0.2s ease' }}>
      <div className="brand" style={{ justifyContent: collapsed ? 'center' : undefined, padding: collapsed ? '18px 0' : undefined }}>
        <div className="brand-mark" aria-hidden="true" style={{ cursor: 'pointer' }} onClick={onToggleCollapse} />
        {!collapsed && <div className="brand-name">Team Diamonds</div>}
      </div>

      <div className="nav-group">
        {NAV.map(n => (
          <NavItem key={n.id} item={n} active={activePage === n.id} onClick={onNavigate} collapsed={collapsed} />
        ))}
      </div>

      <div className="nav-group">
        {!collapsed && <div className="nav-h">My Connected Apps</div>}
        {connectedApps.map(app => (
          <div
            key={app.id}
            className="nav-item"
            title={collapsed ? app.label : undefined}
            style={{ cursor: 'default', justifyContent: collapsed ? 'center' : undefined }}
          >
            <app.Icon />
            {!collapsed && <span>{app.label}</span>}
          </div>
        ))}
        <div
          className="nav-item nav-item--connect"
          onClick={onConnectApp}
          title={collapsed ? 'Connect App' : undefined}
          style={{ justifyContent: collapsed ? 'center' : undefined }}
        >
          <span className="nav-connect-plus">+</span>
          {!collapsed && <span>Connect App</span>}
        </div>
      </div>

      <div className="nav-group">
        {!collapsed && <div className="nav-h">Other</div>}
        {NAV_2.map(n => (
          <NavItem key={n.id} item={n} active={activePage === n.id} onClick={onNavigate} collapsed={collapsed} />
        ))}
      </div>
      <div className="nav-group" style={{ marginTop: 'auto' }}>
        <div
          className="nav-item"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{ justifyContent: collapsed ? 'center' : undefined }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path
              d={collapsed
                ? 'M6 3l5 5-5 5'
                : 'M10 3L5 8l5 5'
              }
              stroke="currentColor"
              strokeWidth="1.3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {!collapsed && <span>Collapse Menu</span>}
        </div>
      </div>

    </aside>
  )
}