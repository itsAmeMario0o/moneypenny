import { formatDollars, formatTokens } from '../format.js'

// A ring that fills up as today's tokens approach the daily budget.
export default function TokenMeter({ usage }) {
  const used = usage.today.total_tokens
  const percent = usage.percent_of_budget

  // The ring is a circle outline. We draw only part of it by making the
  // dash as long as the used share of the circumference.
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const filledShare = Math.min(percent, 100) / 100
  const dashLength = circumference * filledShare

  let color = 'var(--green)'
  if (percent >= 100) {
    color = 'var(--red)'
  } else if (percent >= 70) {
    color = 'var(--orange)'
  }

  return (
    <div className="meter">
      <svg className="meter-ring" width="100" height="100" viewBox="0 0 100 100" role="img"
        aria-label={percent + ' percent of the daily token budget used'}>
        <circle className="meter-track" cx="50" cy="50" r={radius} fill="none" strokeWidth="10" />
        <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="10" strokeLinecap="round"
          stroke={color} strokeDasharray={dashLength + ' ' + circumference} />
      </svg>
      <div className="meter-text">
        <div className="stat-value" style={{ margin: 0 }}>{percent}%</div>
        <div>{formatTokens(used)} of {formatTokens(usage.budget)} tokens today</div>
        <div className="dim small">
          {formatTokens(usage.today.input_tokens)} in · {formatTokens(usage.today.output_tokens)} out ·
          about {formatDollars(usage.today.cost)} · {usage.today.calls} calls
        </div>
      </div>
    </div>
  )
}
