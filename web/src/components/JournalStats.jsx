import { useEffect, useRef, useState } from 'react'
import { createChart, AreaSeries } from 'lightweight-charts'
import Gauge from './Gauge.jsx'

// Trading performance, read from the LuxAlgo trade journal container.
// The journal works out every number; this file only displays them.
// nginx forwards /journal-api/ to the journal's own /api/ (see web/nginx.conf).

// The period buttons. `days` is how far back to look; YTD and All are special.
const PERIODS = [
  { name: '7D', days: 7 },
  { name: '30D', days: 30 },
  { name: '90D', days: 90 },
  { name: 'YTD' },
  { name: 'All' },
]

// The first day of a period as "YYYY-MM-DD", or '' for all time.
function firstDayOf(period) {
  const today = new Date()
  if (period.name === 'All') {
    return ''
  }
  if (period.name === 'YTD') {
    return today.getFullYear() + '-01-01'
  }
  const start = new Date(today.getTime() - period.days * 24 * 60 * 60 * 1000)
  return start.toISOString().slice(0, 10)
}

function formatMoney(amount) {
  const sign = amount < 0 ? '-' : ''
  return sign + '$' + Math.abs(amount).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

function moneyClass(amount) {
  if (amount > 0) {
    return 'good'
  }
  if (amount < 0) {
    return 'bad'
  }
  return ''
}

function percentText(share) {
  return (share * 100).toFixed(1) + '%'
}

// A small card: label on top, then whatever is passed in.
function MetricCard({ label, children }) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      {children}
    </div>
  )
}

// Running total of profit and loss, one point per trading day.
function EquityCurve({ points }) {
  const container = useRef(null)

  useEffect(() => {
    const chart = createChart(container.current, {
      autoSize: true,
      layout: { background: { color: '#1f1f1f' }, textColor: '#b3b3b3' },
      grid: { vertLines: { color: '#252525' }, horzLines: { color: '#252525' } },
    })
    const line = chart.addSeries(AreaSeries, {
      lineColor: '#1ed760', topColor: 'rgba(30, 215, 96, 0.3)', bottomColor: 'rgba(30, 215, 96, 0)',
      lineWidth: 2,
    })
    const data = []
    for (const point of points) {
      data.push({ time: point.t, value: point.cumNetPnl })
    }
    line.setData(data)
    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [points])

  return <div className="chart small-chart" ref={container} />
}

export default function JournalStats({ onOpenJournal }) {
  const [periodName, setPeriodName] = useState('All')
  const [stats, setStats] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  // Load when the period changes, then every 30 seconds.
  useEffect(() => {
    let period = PERIODS[PERIODS.length - 1]
    for (const candidate of PERIODS) {
      if (candidate.name === periodName) {
        period = candidate
      }
    }
    const firstDay = firstDayOf(period)

    async function loadStats() {
      try {
        const response = await fetch('/journal-api/stats' + (firstDay ? '?from=' + firstDay : ''))
        if (!response.ok) {
          throw new Error('the journal answered ' + response.status)
        }
        setStats(await response.json())
        setErrorMessage('')
      } catch (error) {
        setErrorMessage('Cannot reach the trade journal: ' + error.message)
      }
    }

    loadStats()
    const timer = setInterval(loadStats, 30000)
    return () => clearInterval(timer)
  }, [periodName])

  const heading = (
    <div className="section-head">
      <h2>Trading performance</h2>
      <div className="segmented" role="group" aria-label="Period">
        {PERIODS.map((period) => (
          <button key={period.name} className={period.name === periodName ? 'segment active' : 'segment'}
            aria-pressed={period.name === periodName} onClick={() => setPeriodName(period.name)}>
            {period.name}
          </button>
        ))}
      </div>
    </div>
  )

  if (errorMessage) {
    return <>{heading}<div className="banner bad">{errorMessage}</div></>
  }
  if (stats === null) {
    return heading
  }

  // The journal leaves `metrics` empty when accounts use different currencies
  // and no conversion is set up, because the amounts cannot be added together.
  const metrics = stats.metrics
  if (metrics === null || metrics.closedTrades === 0) {
    let message = 'No closed trades in this period.'
    if (metrics === null) {
      message = 'The journal has accounts in more than one currency. Set a display currency in its settings to see totals here.'
    } else if (periodName === 'All') {
      message = 'No closed trades in the journal yet.'
    }
    return (
      <>
        {heading}
        <div className="card" style={{ marginBottom: 16 }}>
          <p className="dim">{message}</p>
          <button className="button" onClick={onOpenJournal}>Open journal</button>
        </div>
      </>
    )
  }

  let profitFactor = '—'
  if (metrics.profitFactorIsInfinite) {
    profitFactor = '∞'
  } else if (metrics.profitFactor !== null) {
    profitFactor = metrics.profitFactor.toFixed(2)
  }

  // Width of the green part of the average win / loss bar.
  const averageWin = metrics.avgWin || 0
  const averageLoss = metrics.avgLoss || 0
  let winShareOfBar = 50
  if (averageWin + averageLoss > 0) {
    winShareOfBar = (averageWin / (averageWin + averageLoss)) * 100
  }

  let streakText = 'none'
  if (metrics.currentStreak > 0) {
    streakText = metrics.currentStreak + ' wins'
  } else if (metrics.currentStreak < 0) {
    streakText = -metrics.currentStreak + ' losses'
  }

  return (
    <>
      {heading}

      <div className="stat-grid">
        <MetricCard label="Net P&L">
          <div className={'stat-value ' + moneyClass(metrics.netPnl)}>{formatMoney(metrics.netPnl)}</div>
          <div className="dim small">{metrics.closedTrades} closed trades · {formatMoney(metrics.fees)} fees</div>
        </MetricCard>
        <MetricCard label="Trade win %">
          <Gauge share={metrics.winRate} color="var(--blue)" label={percentText(metrics.winRate)}
            description={percentText(metrics.winRate) + ' of trades won'} />
          <div className="dim small">{metrics.wins} W · {metrics.breakevens} BE · {metrics.losses} L</div>
        </MetricCard>
        <MetricCard label="Profit factor">
          <div className="stat-value">{profitFactor}</div>
          <div className="dim small">gross profit ÷ gross loss</div>
        </MetricCard>
        <MetricCard label="Day win %">
          <Gauge share={metrics.dayWinRate} color="var(--blue)" label={percentText(metrics.dayWinRate)}
            description={percentText(metrics.dayWinRate) + ' of trading days were profitable'} />
          <div className="dim small">{metrics.tradingDays} trading days</div>
        </MetricCard>
      </div>

      <div className="stat-grid">
        <MetricCard label="Avg win / loss">
          <div className="stat-value">{metrics.avgWinLossRatio === null ? '—' : metrics.avgWinLossRatio.toFixed(2)}</div>
          <div className="ratio-bar" aria-hidden="true">
            <span className="ratio-win" style={{ width: winShareOfBar + '%' }} />
            <span className="ratio-loss" />
          </div>
          <div className="small">
            <span className="good">{formatMoney(averageWin)}</span> <span className="dim">avg win ·</span>{' '}
            <span className="bad">{formatMoney(-averageLoss)}</span> <span className="dim">avg loss</span>
          </div>
        </MetricCard>
        <MetricCard label="Expectancy">
          <div className={'stat-value ' + moneyClass(metrics.expectancy || 0)}>{formatMoney(metrics.expectancy || 0)}</div>
          <div className="dim small">average result per trade</div>
        </MetricCard>
        <MetricCard label="Max drawdown">
          <div className="stat-value bad">{formatMoney(-metrics.maxDrawdown)}</div>
          <div className="dim small">
            {metrics.maxDrawdownPct === null ? 'largest fall from a peak' : percentText(metrics.maxDrawdownPct) + ' from the peak'}
          </div>
        </MetricCard>
        <MetricCard label="Current streak">
          <div className={'stat-value ' + moneyClass(metrics.currentStreak)}>{streakText}</div>
          <div className="dim small">longest: {metrics.maxWinStreak} wins, {metrics.maxLossStreak} losses</div>
        </MetricCard>
      </div>

      <div className="split-grid" style={{ marginBottom: 28 }}>
        <div className="card">
          <div className="stat-label" style={{ marginBottom: 12 }}>Equity curve</div>
          <EquityCurve points={stats.dailyCumulative} />
        </div>
        <div className="card">
          <div className="stat-label" style={{ marginBottom: 12 }}>Recent trades</div>
          <table>
            <tbody>
              {stats.recentTrades.map((trade) => (
                <tr key={trade.key}>
                  <td><b>{trade.symbol}</b></td>
                  <td className="dim">{trade.closedAt.slice(0, 10)}</td>
                  <td className={'number ' + moneyClass(trade.netPnl)}>{formatMoney(trade.netPnl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button className="button" style={{ marginTop: 12 }} onClick={onOpenJournal}>Open journal</button>
        </div>
      </div>
    </>
  )
}
