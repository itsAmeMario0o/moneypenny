import { useEffect, useState } from 'react'
import { getJson } from '../api.js'
import { formatDollars, formatTokens } from '../format.js'
import AgentBoard from './AgentBoard.jsx'

function agentName(agents, key) {
  for (const agent of agents) {
    if (agent.key === key) {
      return agent.name
    }
  }
  return key
}

function statusClass(status) {
  if (status === 'done') {
    return 'badge good'
  }
  if (status === 'error') {
    return 'badge bad'
  }
  return 'badge info'
}

// One TradingAgents run: the live board, the message feed, and the final reports.
// `compact` hides the settings and reports (the thesis page shows those itself).
export default function RunView({ runId, agents, usage, compact }) {
  const [run, setRun] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  async function loadRun() {
    try {
      setRun(await getJson('/runs/' + runId))
    } catch (error) {
      setErrorMessage(error.message)
    }
  }

  useEffect(() => {
    setRun(null)
    loadRun()
  }, [runId])

  // While the run is going, fetch new agent messages every 3 seconds.
  const isRunning = run !== null && run.status === 'running'
  useEffect(() => {
    if (!isRunning) {
      return
    }
    const timer = setInterval(loadRun, 3000)
    return () => clearInterval(timer)
  }, [isRunning, runId])

  if (errorMessage) {
    return <p className="bad">{errorMessage}</p>
  }
  if (run === null) {
    return <p className="dim">Loading run…</p>
  }

  const cost = usage && usage.by_run[run.id]
  const newestFirst = run.events.slice().reverse()

  return (
    <>
      <p>
        <span className={statusClass(run.status)}>{run.status}</span>
        {run.signal && <span className="badge">Verdict: {run.signal}</span>}
        <span className="badge">{run.trade_date}</span>
        {!compact && <span className="badge">depth {run.settings.depth}</span>}
        {!compact && <span className="badge">{run.settings.deep_model} / {run.settings.quick_model}</span>}
        {cost && <span className="badge">{formatTokens(cost.total_tokens)} tokens · {formatDollars(cost.cost)}</span>}
      </p>
      {run.error && <div className="banner bad">{run.error}</div>}

      <AgentBoard agents={agents} run={run} />

      <h2 style={{ marginTop: 20 }}>Agent messages</h2>
      {run.events.length === 0 && (
        <p className="dim">{isRunning ? 'Waiting for the first analyst to report. This can take a minute.' : 'No messages were recorded.'}</p>
      )}
      {newestFirst.map((event) => (
        <details key={event.id} className="event">
          <summary>
            <b>{agentName(agents, event.agent)}</b>
            <span className="dim small"> · {event.created.slice(11, 19)} UTC · {event.text.slice(0, 110)}…</span>
          </summary>
          <pre>{event.text}</pre>
        </details>
      ))}

      {!compact && run.reports && (
        <>
          <h2 style={{ marginTop: 20 }}>Final reports</h2>
          {Object.keys(run.reports).map((name) => run.reports[name] && (
            <details key={name}>
              <summary>{name.replaceAll('_', ' ')}</summary>
              <pre>{run.reports[name]}</pre>
            </details>
          ))}
        </>
      )}
    </>
  )
}
