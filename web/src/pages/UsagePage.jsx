import TokenMeter from '../components/TokenMeter.jsx'
import { formatDollars, formatTokens } from '../format.js'

// One table of token totals. `groups` is an object like { thesis: {...totals}, research: {...totals} }.
function UsageTable({ title, firstColumn, groups, labelFor }) {
  const names = Object.keys(groups)
  return (
    <div className="card">
      <h2>{title}</h2>
      {names.length === 0 && <p className="dim">Nothing recorded yet.</p>}
      {names.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>{firstColumn}</th><th className="number">Calls</th><th className="number">Input</th>
              <th className="number">Output</th><th className="number">Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {names.map((name) => (
              <tr key={name}>
                <td>{labelFor ? labelFor(name) : name}</td>
                <td className="number">{groups[name].calls}</td>
                <td className="number">{formatTokens(groups[name].input_tokens)}</td>
                <td className="number">{formatTokens(groups[name].output_tokens)}</td>
                <td className="number">{formatDollars(groups[name].cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function UsagePage({ usage, theses }) {
  if (!usage) {
    return <p className="dim">Loading…</p>
  }

  function thesisLabel(thesisId) {
    for (const thesis of theses) {
      if (String(thesis.id) === thesisId) {
        return thesis.ticker + ' #' + thesis.id
      }
    }
    return 'Thesis #' + thesisId
  }

  return (
    <div className="stack">
      <div className="card">
        <h2>Today (UTC)</h2>
        <TokenMeter usage={usage} />
        <p className="dim small" style={{ marginTop: 12 }}>
          All time: {formatTokens(usage.all_time.total_tokens)} tokens, about {formatDollars(usage.all_time.cost)}.
          Costs are estimates at standard API prices. Change the budget with DAILY_TOKEN_BUDGET in .env.
        </p>
      </div>
      <UsageTable title="By pipeline step" firstColumn="Step" groups={usage.by_step} />
      <UsageTable title="By model" firstColumn="Model" groups={usage.by_model} />
      <UsageTable title="By thesis" firstColumn="Thesis" groups={usage.by_thesis} labelFor={thesisLabel} />
    </div>
  )
}
