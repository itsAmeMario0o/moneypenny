import Gauge from '../components/Gauge.jsx'
import JournalStats from '../components/JournalStats.jsx'
import TokenMeter from '../components/TokenMeter.jsx'
import { directionClass, formatDollars, formatTokens, sentimentClass, stepsDone } from '../format.js'

function StatCard({ label, value, note }) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="dim small">{note}</div>
    </div>
  )
}

// Five small bars; the first `done` are green.
function StepDots({ done }) {
  const dots = []
  for (let step = 1; step <= 5; step++) {
    dots.push(<span key={step} className={step <= done ? 'step-dot done' : 'step-dot'} />)
  }
  return <div className="steps" title={done + ' of 5 steps done'}>{dots}</div>
}

function countWithStatus(theses, statuses) {
  let count = 0
  for (const thesis of theses) {
    if (statuses.includes(thesis.status)) {
      count = count + 1
    }
  }
  return count
}

export default function Dashboard({ theses, runs, usage, onOpenThesis, onOpenRun, onOpenJournal }) {
  const running = countWithStatus(runs, ['running'])
  const recentRuns = runs.slice(0, 5)
  const strategiesReady = countWithStatus(theses, ['strategy', 'charted'])
  const failed = countWithStatus(theses, ['error'])

  // The newest thesis that has a sentiment score (-1 bearish to +1 bullish).
  let latestScored = null
  for (const thesis of theses) {
    if (latestScored === null && thesis.sentiment !== null) {
      latestScored = thesis
    }
  }
  let sentimentColor = 'var(--text-dim)'
  if (latestScored !== null && sentimentClass(latestScored.sentiment) === 'good') {
    sentimentColor = 'var(--green)'
  } else if (latestScored !== null && sentimentClass(latestScored.sentiment) === 'bad') {
    sentimentColor = 'var(--red)'
  }

  return (
    <>
      <JournalStats onOpenJournal={onOpenJournal} />

      <div className="section-head">
        <h2>Research desk</h2>
      </div>

      <div className="stat-grid">
        <StatCard label="Theses" value={theses.length} note={strategiesReady + ' with a strategy · ' + failed + ' with errors'} />
        <StatCard label="Agents running" value={running} note={runs.length + ' runs in total'} />
        <div className="card">
          <div className="stat-label">News sentiment</div>
          {latestScored === null && <div className="stat-value">—</div>}
          {latestScored !== null && (
            <Gauge share={(latestScored.sentiment + 1) / 2} color={sentimentColor}
              label={(latestScored.sentiment > 0 ? '+' : '') + latestScored.sentiment.toFixed(2)}
              description={'News sentiment ' + latestScored.sentiment.toFixed(2) + ' on a scale from minus one to plus one'} />
          )}
          <div className="dim small">{latestScored === null ? 'no thesis yet' : 'latest thesis: ' + latestScored.ticker + ' · −1 bearish to +1 bullish'}</div>
        </div>
        <StatCard label="Spend today" value={usage ? formatDollars(usage.today.cost) : '—'}
          note={usage ? formatTokens(usage.today.total_tokens) + ' tokens (estimate)' : ''} />
      </div>

      <div className="split-grid">
        <div className="card">
          <h2>Pipeline</h2>
          {theses.length === 0 && <p className="dim">No theses yet. Enter a ticker above to pull its news and form one.</p>}
          {theses.length > 0 && (
            <table>
              <thead>
                <tr><th>Ticker</th><th>Direction</th><th className="number">Sentiment</th><th>Progress</th><th>Status</th></tr>
              </thead>
              <tbody>
                {theses.map((thesis) => (
                  <tr key={thesis.id} className="row-button" tabIndex={0}
                    onClick={() => onOpenThesis(thesis.id)}
                    onKeyDown={(event) => { if (event.key === 'Enter') onOpenThesis(thesis.id) }}>
                    <td><b>{thesis.ticker}</b> <span className="dim small">#{thesis.id}</span></td>
                    <td>{thesis.direction && <span className={'badge ' + directionClass(thesis.direction)}>{thesis.direction}</span>}</td>
                    <td className={'number ' + sentimentClass(thesis.sentiment || 0)}>
                      {thesis.sentiment === null ? '—' : thesis.sentiment.toFixed(2)}
                    </td>
                    <td><StepDots done={stepsDone(thesis)} /></td>
                    <td className={thesis.status === 'error' ? 'bad' : 'dim'}>{thesis.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="stack">
          <div className="card">
            <h2>Token meter</h2>
            {usage ? <TokenMeter usage={usage} /> : <p className="dim">Loading…</p>}
          </div>
          <div className="card">
            <h2>Recent agent runs</h2>
            {recentRuns.length === 0 && <p className="dim">No runs yet. Start one from Agent runs, or from step 3 of a thesis.</p>}
            {recentRuns.length > 0 && (
              <table>
                <tbody>
                  {recentRuns.map((run) => (
                    <tr key={run.id} className="row-button" tabIndex={0}
                      onClick={() => onOpenRun(run.id)}
                      onKeyDown={(event) => { if (event.key === 'Enter') onOpenRun(run.id) }}>
                      <td><b>{run.ticker}</b> <span className="dim small">#{run.id}</span></td>
                      <td><b>{run.signal || '—'}</b></td>
                      <td className={run.status === 'error' ? 'bad' : run.status === 'running' ? 'info' : 'dim'}>{run.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
