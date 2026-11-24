import { useEffect, useState } from 'react'
import { getJson, postJson } from './api.js'
import RunView from './components/RunView.jsx'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import RunsPage from './pages/RunsPage.jsx'
import ThesisPage from './pages/ThesisPage.jsx'
import ToolsPage from './pages/ToolsPage.jsx'
import UsagePage from './pages/UsagePage.jsx'

const PAGE_TITLES = {
  dashboard: 'Mission control',
  runs: 'Agent runs',
  run: 'Run',
  journal: 'Trade journal',
  tools: 'Tools',
  usage: 'Token usage',
  thesis: 'Thesis',
}

// The app shell: sidebar on the left, header on top, one page in the middle.
// There is no router; `page` says which page to show.
export default function App() {
  const [page, setPage] = useState('dashboard')
  const [selectedThesisId, setSelectedThesisId] = useState(null)
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [theses, setTheses] = useState([])
  const [runs, setRuns] = useState([])
  const [usage, setUsage] = useState(null)
  const [health, setHealth] = useState(null)
  const [ticker, setTicker] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  async function refresh() {
    try {
      setTheses(await getJson('/theses'))
      setRuns(await getJson('/runs'))
      setUsage(await getJson('/usage'))
      setHealth(await getJson('/health'))
    } catch (error) {
      setErrorMessage('Cannot reach the API: ' + error.message)
    }
  }

  // Load once at the start, then every 10 seconds so the numbers stay current.
  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 10000)
    return () => clearInterval(timer)
  }, [])

  function openThesis(thesisId) {
    setSelectedThesisId(thesisId)
    setPage('thesis')
  }

  function openRun(runId) {
    setSelectedRunId(runId)
    setPage('run')
  }

  async function createThesis(event) {
    event.preventDefault()
    setIsCreating(true)
    setErrorMessage('')
    try {
      const thesis = await postJson('/theses', { ticker: ticker })
      setTicker('')
      openThesis(thesis.id)
    } catch (error) {
      setErrorMessage(error.message)
    }
    setIsCreating(false)
    refresh()
  }

  let title = PAGE_TITLES[page]
  if (page === 'thesis') {
    for (const thesis of theses) {
      if (thesis.id === selectedThesisId) {
        title = thesis.ticker + ' thesis #' + thesis.id
      }
    }
  }
  if (page === 'run') {
    for (const run of runs) {
      if (run.id === selectedRunId) {
        title = run.ticker + ' run #' + run.id
      }
    }
  }

  return (
    <div className="layout">
      <Sidebar page={page} selectedId={selectedThesisId} theses={theses} health={health}
        onShowPage={setPage} onOpenThesis={openThesis} />

      <main className="main">
        <div className="header">
          <h1>{title}</h1>
          <form className="ticker-form" onSubmit={createThesis}>
            <input className="input" placeholder="Ticker, e.g. NVDA" aria-label="Ticker"
              value={ticker} onChange={(event) => setTicker(event.target.value)} required />
            <button className="button primary" disabled={isCreating}>
              {isCreating ? 'Reading news…' : 'New thesis'}
            </button>
          </form>
        </div>

        {health && !health.api_key_set && (
          <div className="banner warn">
            No Anthropic API key yet. Add it to <code>.env</code> as <code>ANTHROPIC_API_KEY</code>, then run <code>docker compose up -d</code>.
          </div>
        )}
        {errorMessage && <div className="banner bad">{errorMessage}</div>}

        {/* The key makes React start a page fresh each time you switch to it. */}
        <div className="fade-in" key={page + selectedThesisId + selectedRunId}>
          {page === 'dashboard' && <Dashboard theses={theses} runs={runs} usage={usage} onOpenThesis={openThesis} onOpenRun={openRun} onOpenJournal={() => setPage('journal')} />}
          {page === 'runs' && health && <RunsPage runs={runs} defaults={health.run_defaults} onOpenRun={openRun} onChanged={refresh} />}
          {page === 'run' && health && <div className="card"><RunView runId={selectedRunId} agents={health.agents} usage={usage} /></div>}
          {/* The journal is a separate app (its own container on port 3000), shown inside ours. */}
          {page === 'journal' && <iframe className="journal-frame" title="Trade journal" src={'http://' + window.location.hostname + ':3000'} />}
          {page === 'tools' && <ToolsPage />}
          {page === 'usage' && <UsagePage usage={usage} theses={theses} />}
          {page === 'thesis' && health && <ThesisPage thesisId={selectedThesisId} agents={health.agents} usage={usage} onOpenRun={openRun} onChanged={refresh} />}
        </div>
      </main>
    </div>
  )
}
