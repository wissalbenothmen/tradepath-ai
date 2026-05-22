interface Props {
  values: number[]
  width?: number
  height?: number
  tone?: 'brand' | 'success' | 'danger' | 'ai'
  /** Render last data point as a dot. */
  showDot?: boolean
}

/** Tiny inline sparkline (no Recharts needed). */
export default function Sparkline({
  values,
  width = 96,
  height = 28,
  tone = 'brand',
  showDot = true,
}: Props) {
  if (!values.length) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const stepX = values.length === 1 ? 0 : width / (values.length - 1)
  const points = values.map((v, i) => {
    const x = i * stepX
    const y = height - ((v - min) / range) * height
    return [x, y] as const
  })
  const path = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const colors = {
    brand: { stroke: '#3460ff', fill: 'rgb(52 96 255 / 0.12)' },
    success: { stroke: '#16a34a', fill: 'rgb(22 163 74 / 0.12)' },
    danger: { stroke: '#dc2626', fill: 'rgb(220 38 38 / 0.12)' },
    ai: { stroke: '#7c3aed', fill: 'rgb(124 58 237 / 0.12)' },
  }[tone]
  const [lastX, lastY] = points[points.length - 1]
  const areaPath = `${path} L ${width} ${height} L 0 ${height} Z`
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <path d={areaPath} fill={colors.fill} />
      <path d={path} stroke={colors.stroke} strokeWidth="1.6" fill="none" strokeLinejoin="round" strokeLinecap="round" />
      {showDot && (
        <circle cx={lastX} cy={lastY} r={2.4} fill={colors.stroke}>
          <animate attributeName="r" values="2.4;3.4;2.4" dur="1.8s" repeatCount="indefinite" />
        </circle>
      )}
    </svg>
  )
}
