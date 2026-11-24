import { useEffect, useState } from 'react'
import { getJson, postJson } from '../api.js'
import PriceChart from '../components/PriceChart.jsx'
import RunView from '../components/RunView.jsx'
import { directionClass, sentimentClass } from '../format.js'

const REPORT_NAMES = ['final_trade_decision', 'investment_plan', 'market_report', 'sentiment_report', 'news_report', 'fundamentals_report']

function SectionTitle({ number, title, done }) {
  return (
    <h2>
      <span className={done ? 'section-number done' : 'section-number'}>{number}</span>
      {title}
    </h2>
  )
}

// One thesis, shown as the five pipeline steps from top to bottom.
export default function ThesisPage({ thesisId, agents, usage, onOpenRun, onChanged }) {
  const [thesis, setThesis] = useState(null)
  const [busyStep, setBusyStep] = useState('')  // which button is working: '', 'research' or 'strategy'
  const [errorMessage, setErrorMessage] = useState('')

  async function loadThesis() {
    try {
      setThesis(await getJson('/theses/' + thesisId))
    } catch (error) {
      setErrorMessage(error.message)
    }
  }

  // Load when the page opens or a different thesis is picked.
  useEffect(() => {
    setThesis(null)
    setErrorMessage('')
    loadThesis()
  }, [thesisId])

  // While research runs in the background, check on it every 4 seconds.
  const isResearching = thesis !== null && thesis.status === 'researching'
  useEffect(() => {
    if (!isResearching) {
      return
    }
    const timer = setInterval(loadThesis, 4000)
    return () => clearInterval(timer)
  }, [isResearching, thesisId])

  async function runStep(stepName) {
    setBusyStep(stepName)
    setErrorMessage('')
    try {
      await postJson('/theses/' + thesisId + '/' + stepName)
    } catch (error) {
      setErrorMessage(error.message)
    }
    await loadThesis()
    setBusyStep('')
    onChanged()
  }

  if (thesis === null) {
    return <p className={errorMessage ? 'bad' : 'dim'}>{errorMessage || 'Loading…'}</p>
  }

  const analysis = thesis.analysis
  const research = thesis.research
  const strategy = thesis.strategy
  const chartResult = thesis.chart
  const headlines = analysis ? analysis.headlines : (thesis.news || [])

  return (
    <>
      {errorMessage && <div className="banner bad">{errorMessage}</div>}
      {thesis.error && <div className="banner bad">{thesis.error}</div>}

      <div className="card section">
        <SectionTitle number={1} title="News" done={true} />
        {analysis && (
          <p className="dim">Overall sentiment <b className={sentimentClass(analysis.overall_sentiment)}>{analysis.overall_sentiment.toFixed(2)}</b> (−1 bearish to +1 bullish)</p>
        )}
        <table>
          <tbody>
            {headlines.map((headline, index) => {
              const source = thesis.news && thesis.news[index]
              return (
                <tr key={index}>
                  <td>
                    {source && source.url
                      ? <a href={source.url} target="_blank" rel="noreferrer">{headline.title}</a>
                      : headline.title}
                  </td>
                  <td className={'number ' + sentimentClass(headline.sentiment || 0)}>
                    {headline.sentiment === undefined ? '' : headline.sentiment.toFixed(2)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {analysis && (
        <div className="card section">
          <SectionTitle number={2} title="Thesis" done={true} />
          <p>
            <span className={'badge ' + directionClass(analysis.thesis.direction)}>{analysis.thesis.direction}</span>
            <span className="badge">{analysis.thesis.timeframe}</span>
          </p>
          <p>{analysis.thesis.statement}</p>
          <p className="dim"><b>Catalyst:</b> {analysis.thesis.catalyst}</p>
          <p className="dim"><b>Invalidated if:</b> {analysis.thesis.invalidation}</p>
        </div>
      )}

      {analysis && (
        <div className="card section">
          <SectionTitle number={3} title="Research" done={Boolean(research)} />
          {!isResearching && (
            <button className={research ? 'button' : 'button primary'} disabled={busyStep !== ''} onClick={() => runStep('research')}>
              {research ? 'Run again' : 'Run research'}
            </button>
          )}
          {thesis.latest_run_id && (
            <div style={{ marginTop: 14 }}>
              <RunView runId={thesis.latest_run_id} agents={agents} usage={usage} compact={true} />
              <button className="button" style={{ marginTop: 12 }} onClick={() => onOpenRun(thesis.latest_run_id)}>Open full run</button>
            </div>
          )}
          {research && (
            <>
              <p style={{ marginTop: 12 }}>Verdict: <b>{research.signal}</b></p>
              {REPORT_NAMES.map((name) => research[name] && (
                <details key={name}>
                  <summary>{name.replaceAll('_', ' ')}</summary>
                  <pre>{research[name]}</pre>
                </details>
              ))}
            </>
          )}
        </div>
      )}

      {analysis && (
        <div className="card section">
          <SectionTitle number={4} title="Strategy" done={Boolean(strategy)} />
          <button className={strategy ? 'button' : 'button primary'} disabled={busyStep !== '' || isResearching} onClick={() => runStep('strategy')}>
            {busyStep === 'strategy' ? 'Building… about a minute' : strategy ? 'Rebuild' : research ? 'Build strategy' : 'Build without research'}
          </button>
          {strategy && (
            <>
              <p style={{ marginTop: 12 }}>
                <b>{strategy.name}</b>{' '}
                <span className="badge">{strategy.setup}</span>
                <span className={'badge ' + directionClass(strategy.direction)}>{strategy.direction}</span>
              </p>
              <p><b>Entry:</b> {strategy.entry_rule}</p>
              <p><b>Exit:</b> {strategy.exit_rule}</p>
              <table>
                <thead><tr><th>Level</th><th>Kind</th><th className="number">Price</th></tr></thead>
                <tbody>
                  {strategy.levels.map((level, index) => (
                    <tr key={index}>
                      <td>{level.label}</td>
                      <td className="dim">{level.kind}</td>
                      <td className="number">{level.price.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="dim" style={{ marginTop: 10 }}>{strategy.risk_notes}</p>
              <details>
                <summary>Pine Script</summary>
                <pre>{strategy.pine_script}</pre>
                <button className="button" onClick={() => navigator.clipboard.writeText(strategy.pine_script)}>Copy</button>
              </details>
            </>
          )}
        </div>
      )}

      {strategy && (
        <div className="card section">
          <SectionTitle number={5} title="Chart" done={Boolean(chartResult)} />
          <PriceChart ticker={thesis.ticker} levels={strategy.levels} />
          <p className="dim" style={{ marginTop: 12 }}>
            To mark this up in TradingView and backtest the Pine Script, run <code>/chart-thesis {thesis.id}</code> in Claude Code.
          </p>
          {chartResult && (
            <details open>
              <summary>TradingView result</summary>
              <pre>{JSON.stringify(chartResult, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </>
  )
}
