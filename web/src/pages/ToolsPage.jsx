import { useEffect, useState } from 'react'
import { getJson, postJson } from '../api.js'

// Shows whatever a tool returned:
//   a list of objects -> a table with one column per key
//   one object        -> a two-column name/value table
//   anything else     -> the raw JSON
function ResultView({ result }) {
  const isList = Array.isArray(result)

  if (isList && result.length > 0 && typeof result[0] === 'object') {
    const columns = Object.keys(result[0])
    return (
      <table>
        <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>
          {result.map((row, index) => (
            <tr key={index}>{columns.map((column) => <td key={column}>{String(row[column])}</td>)}</tr>
          ))}
        </tbody>
      </table>
    )
  }

  if (!isList && result !== null && typeof result === 'object') {
    return (
      <table>
        <tbody>
          {Object.keys(result).map((name) => (
            <tr key={name}><td className="dim">{name}</td><td className="number">{String(result[name])}</td></tr>
          ))}
        </tbody>
      </table>
    )
  }

  return <pre>{JSON.stringify(result, null, 2)}</pre>
}

// Every file in api/tools/ shows up here with a Run button.
export default function ToolsPage() {
  const [tools, setTools] = useState([])
  const [ticker, setTicker] = useState('')
  const [busyTool, setBusyTool] = useState('')
  const [output, setOutput] = useState(null)  // { tool, ticker, result }
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    getJson('/tools').then(setTools).catch((error) => setErrorMessage(error.message))
  }, [])

  async function runTool(name) {
    if (ticker.trim() === '') {
      setErrorMessage('Enter a ticker first.')
      return
    }
    setBusyTool(name)
    setErrorMessage('')
    try {
      setOutput(await postJson('/tools/' + name, { ticker: ticker }))
    } catch (error) {
      setErrorMessage(error.message)
    }
    setBusyTool('')
  }

  return (
    <div className="stack">
      <div className="card">
        <h2>Run a tool</h2>
        <input className="input" placeholder="Ticker, e.g. NVDA" aria-label="Ticker"
          value={ticker} onChange={(event) => setTicker(event.target.value)} />
        {errorMessage && <p className="bad" style={{ marginTop: 10 }}>{errorMessage}</p>}
        <table style={{ marginTop: 16 }}>
          <tbody>
            {tools.map((tool) => (
              <tr key={tool.name}>
                <td><b>{tool.title}</b></td>
                <td className="dim">{tool.description}</td>
                <td className="number">
                  <button className="button" disabled={busyTool !== ''} onClick={() => runTool(tool.name)}>
                    {busyTool === tool.name ? 'Running…' : 'Run'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="dim small" style={{ marginTop: 12 }}>
          To add a tool, put a new Python file in <code>api/tools/</code>. The instructions are at the top of <code>api/tools/__init__.py</code>.
        </p>
      </div>

      {output && (
        <div className="card fade-in" key={output.tool + output.ticker}>
          <h2>{output.tool.replaceAll('_', ' ')} · {output.ticker}</h2>
          <ResultView result={output.result} />
        </div>
      )}
    </div>
  )
}
