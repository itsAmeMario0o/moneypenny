// A half-circle gauge. `share` runs from 0 (empty) to 1 (full).
export default function Gauge({ share, color, label, description }) {
  // The arc is half of a circle with radius 50, so its length is pi * 50.
  // We draw only part of it by making the dash as long as the filled share.
  const arcLength = Math.PI * 50
  const filledShare = Math.max(0, Math.min(share, 1))
  const arcPath = 'M 10 60 A 50 50 0 0 1 110 60'

  return (
    <div className="gauge">
      <svg width="120" height="68" viewBox="0 0 120 68" role="img" aria-label={description}>
        <path className="meter-track" d={arcPath} fill="none" strokeWidth="10" strokeLinecap="round" />
        <path className="gauge-fill" d={arcPath} fill="none" strokeWidth="10" strokeLinecap="round"
          stroke={color} strokeDasharray={arcLength * filledShare + ' ' + arcLength} />
      </svg>
      <div className="gauge-label">{label}</div>
    </div>
  )
}
