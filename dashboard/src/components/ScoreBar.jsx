export default function ScoreBar({ label, score }) {
  const pct = Math.round(score * 100)
  const barColor = pct >= 80 ? 'bg-brand-green' : pct >= 50 ? 'bg-brand-yellow' : 'bg-rose-500'
  return (
    <div className="flex items-center gap-3">
      <span className="text-slate-400 text-xs w-28 shrink-0 truncate" title={label}>{label}</span>
      <div className="flex-1 bg-white/5 rounded-full h-2">
        <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs w-8 text-right font-mono ${pct >= 80 ? 'text-brand-green' : pct >= 50 ? 'text-brand-yellow' : 'text-rose-400'}`}>
        {pct}%
      </span>
    </div>
  )
}
