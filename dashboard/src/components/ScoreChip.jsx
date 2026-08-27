export default function ScoreChip({ score, size = 'sm' }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'text-brand-green' : pct >= 50 ? 'text-brand-yellow' : 'text-rose-400'
  const text = size === 'lg' ? 'text-4xl font-bold' : 'text-sm font-mono'
  return <span className={`${color} ${text}`}>{pct}%</span>
}
