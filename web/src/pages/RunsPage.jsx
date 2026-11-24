import { useState } from 'react'
import { postJson } from '../api.js'

const ANALYSTS = [
  { key: 'market', label: 'Market' },
  { key: 'social', label: 'Sentiment' },
  { key: 'news', label: 'News' },
  { key: 'fundamentals', label: 'Fundamentals' },
]

// Start a TradingAgents run with your own settings, and see every past run.
export default function RunsPage({ runs, defaults, onOpenRun, onChanged }) {
  const [ticker, setTicker] = useState('')
  const [tradeDate, setTradeDate] = useState('')
  const [selected, setSelected] = useState({ market: true, social: true, news: true, fundamentals: true })
  const [depth, setDepth] = useState(1)
  const [deepModel, setDeepModel] = useState(defaults.deep_model)
  const [quickModel, setQuickModel] = useState(defaults.quick_model)
  const [isStarting, setIsStarting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  function toggleAnalyst(key) {
    const copy = { ...selected }
    copy[key] = !copy[key]
    setSelected(copy)
  }

  async function startRun(event) {
    event.preventDefault()
    const analysts = []
    for (const analyst of ANALYSTS) {
      if (selected[analyst.key]) {
        analysts.push(analyst.key)
      }
    }
    if (analysts.length === 0) {
      setErrorMessage('Pick at least one analyst.')
      return
    }

    setIsStarting(true)
    setErrorMessage('')
    try {
      const reply = await postJson('/runs', {
        ticker: ticker,
        trade_date: tradeDate,
        analysts: analysts,
        depth: depth,
        deep_model: deepModel,
        quick_model: quickModel,
      })
      onChanged()
      onOpenRun(reply.run_id)
    } catch (error) {
      setErrorMessage(error.message)
    }
    setIsStarting(false)
  }

  return (
    <div className="stack">
      <form className="card" onSubmit={startRun}>
        <h2>New run</h2>
        {errorMessage && <p className="bad">{errorMessage}</p>}
        <div className="form-grid">
          <label>Ticker
            <input className="input" value={ticker} onChange={(event) => setTicker(event.target.value)} placeholder="e.g. NVDA" required />
          </label>
          <label>Analysis date
            <input className="input" type="date" value={tradeDate} onChange={(event) => setTradeDate(event.target.value)} />
          </label>
          <label>Research depth
            <select className="input" value={depth} onChange={(event) => setDepth(Number(event.target.value))}>
              <option value={1}>1 debate round (fastest)</option>
              <option value={2}>2 debate rounds</option>
              <option value={3}>3 debate rounds (most tokens)</option>
            </select>
          </label>
          <label>Deep-thinking model
            <input className="input plain" value={deepModel} onChange={(event) => setDeepModel(event.target.value)} />
          </label>
          <label>Quick model
            <input className="input plain" value={quickModel} onChange={(event) => setQuickModel(event.target.value)} />
          </label>
        </div>
        <fieldset className="checks">
          <legend>Analysts</legend>
          {ANALYSTS.map((analyst) => (
            <label key={analyst.key}>
              <input type="checkbox" checked={selected[analyst.key]} onChange={() => toggleAnalyst(analyst.key)} /> {analyst.label}
            </label>
          ))}
        </fieldset>
        <button className="button primary" disabled={isStarting}>{isStarting ? 'Starting…' : 'Start run'}</button>
        <span className="dim small" style={{ marginLeft: 12 }}>Leave the date empty for today. A run takes several minutes.</span>
      </form>

      <div className="card">
        <h2>History</h2>
        {runs.length === 0 && <p className="dim">No runs yet.</p>}
        {runs.length > 0 && (
          <table>
            <thead>
              <tr><th>Run</th><th>Date</th><th>Analysts</th><th>Depth</th><th>Verdict</th><th>Status</th></tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="row-button" tabIndex={0}
                  onClick={() => onOpenRun(run.id)}
                  onKeyDown={(event) => { if (event.key === 'Enter') onOpenRun(run.id) }}>
                  <td><b>{run.ticker}</b> <span className="dim small">#{run.id}{run.thesis_id ? ' · thesis #' + run.thesis_id : ''}</span></td>
                  <td>{run.trade_date}</td>
                  <td className="dim">{run.settings.analysts.length} of 4</td>
                  <td className="dim">{run.settings.depth}</td>
                  <td><b>{run.signal || '—'}</b></td>
                  <td className={run.status === 'error' ? 'bad' : run.status === 'running' ? 'info' : 'dim'}>{run.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
