// Formatting helpers shared by the pages.

// 1234567 -> "1.23M", 45600 -> "45.6K", 812 -> "812"
export function formatTokens(count) {
  if (count >= 1000000) {
    return (count / 1000000).toFixed(2) + 'M'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1) + 'K'
  }
  return String(count)
}

export function formatDollars(amount) {
  return '$' + amount.toFixed(2)
}

// Sentiment runs from -1 (bearish) to +1 (bullish). Returns a CSS class name.
export function sentimentClass(score) {
  if (score > 0.15) {
    return 'good'
  }
  if (score < -0.15) {
    return 'bad'
  }
  return 'dim'
}

export function directionClass(direction) {
  if (direction === 'long') {
    return 'good'
  }
  if (direction === 'short') {
    return 'bad'
  }
  return ''
}

// How many of the five pipeline steps a thesis summary has finished.
export function stepsDone(thesis) {
  if (thesis.status === 'charted') {
    return 5
  }
  if (thesis.setup) {
    return 4
  }
  if (thesis.signal) {
    return 3
  }
  if (thesis.direction) {
    return 2
  }
  return 1
}
