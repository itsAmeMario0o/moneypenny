import { FiActivity, FiBookOpen, FiCpu, FiGrid, FiTool } from 'react-icons/fi'

// Left navigation: a narrow rail of icons. Hovering it (or tabbing into it)
// widens it to show the labels, the recent theses and the connection status.
// The widening is done in theme.css, not here.
export default function Sidebar({ page, selectedId, theses, health, onShowPage, onOpenThesis }) {
  const recentTheses = theses.slice(0, 8)

  function navClass(isActive) {
    return isActive ? 'nav-item active' : 'nav-item'
  }

  // One icon button. The label is always in the page (for screen readers);
  // it is only invisible while the rail is narrow.
  function navButton(Icon, label, isActive, targetPage) {
    return (
      <button className={navClass(isActive) + ' with-icon'} title={label} onClick={() => onShowPage(targetPage)}>
        <Icon className="nav-icon" aria-hidden="true" />
        <span className="nav-label">{label}</span>
      </button>
    )
  }

  return (
    <nav className="sidebar">
      <div className="brand">
        <span className="brand-mark">M</span> <span className="nav-label">Moneypenny</span>
      </div>

      <div>
        <div className="nav-group-title nav-label">General</div>
        {navButton(FiGrid, 'Mission control', page === 'dashboard', 'dashboard')}
        {navButton(FiCpu, 'Agent runs', page === 'runs' || page === 'run', 'runs')}
        {navButton(FiBookOpen, 'Trade journal', page === 'journal', 'journal')}
        {navButton(FiTool, 'Tools', page === 'tools', 'tools')}
        {navButton(FiActivity, 'Token usage', page === 'usage', 'usage')}
      </div>

      <div className="rail-hidden">
        <div className="nav-group-title">Recent theses</div>
        {recentTheses.length === 0 && <div className="dim small" style={{ padding: '0 12px' }}>None yet</div>}
        {recentTheses.map((thesis) => (
          <button key={thesis.id}
            className={navClass(page === 'thesis' && selectedId === thesis.id)}
            onClick={() => onOpenThesis(thesis.id)}>
            <span>{thesis.ticker}</span>
            <span className="small dim">#{thesis.id} · {thesis.status}</span>
          </button>
        ))}
      </div>

      {health && (
        <div className="sidebar-footer small dim">
          <div title={health.api_key_set ? 'Claude connected' : 'Claude key missing'}>
            <span className={health.api_key_set ? 'dot on' : 'dot off'} />
            <span className="nav-label">Claude {health.api_key_set ? 'connected' : 'key missing'}</span>
          </div>
          <div title={health.telegram_on ? 'Telegram on' : 'Telegram off'}>
            <span className={health.telegram_on ? 'dot on' : 'dot'} />
            <span className="nav-label">Telegram {health.telegram_on ? 'on' : 'off'}</span>
          </div>
        </div>
      )}
    </nav>
  )
}
