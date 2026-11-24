import { useEffect, useRef } from 'react'
import { createChart, CandlestickSeries } from 'lightweight-charts'
import { getJson } from '../api.js'

const LEVEL_COLORS = {
  entry: '#539df5',
  stop: '#f3727f',
  target: '#1ed760',
  support: '#b3b3b3',
  resistance: '#b3b3b3',
}

// Daily candles with one horizontal line per strategy level.
export default function PriceChart({ ticker, levels }) {
  const container = useRef(null)

  useEffect(() => {
    const chart = createChart(container.current, {
      autoSize: true,
      layout: { background: { color: '#1f1f1f' }, textColor: '#b3b3b3' },
      grid: { vertLines: { color: '#252525' }, horzLines: { color: '#252525' } },
    })
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: '#1ed760', wickUpColor: '#1ed760',
      downColor: '#f3727f', wickDownColor: '#f3727f',
      borderVisible: false,
    })

    async function loadBars() {
      const bars = await getJson('/bars/' + ticker)
      candles.setData(bars)
      for (const level of levels) {
        candles.createPriceLine({
          price: level.price,
          color: LEVEL_COLORS[level.kind],
          lineWidth: 1,
          lineStyle: level.kind === 'entry' ? 0 : 2, // 0 = solid, 2 = dashed
          title: level.label,
        })
      }
      // show the last 60 days
      chart.timeScale().setVisibleLogicalRange({ from: bars.length - 60, to: bars.length + 3 })
    }
    loadBars().catch(() => {})

    // remove the chart when the component goes away or its inputs change
    return () => chart.remove()
  }, [ticker, levels])

  return <div className="chart" ref={container} />
}
