import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ScoreBar from '../components/ScoreBar'
import ScoreChip from '../components/ScoreChip'

function avg(runs, key) {
  if (!runs.length) return null
  const vals = runs.map(r => key ? (r.scores?.[key] ?? 0) : r.total_score)
  return vals.reduce((s, v) => s + v, 0) / vals.length
}

function avgJudge(runs) {
  const judged = runs.filter(r => r.judge_met != null && r.judge_total)
  if (!judged.length) return null
  return judged.reduce((s, r) => s + r.judge_met / r.judge_total, 0) / judged.length
}

function fmtPct(v) {
  return v == null ? '—' : `${Math.round(v * 100)}%`
}

const CAT_SHORT = {
  'monitoring_&_observability': 'Monitoring',
  'cloud_financial_management': 'FinOps',
  'operations_management': 'Operations',
  'cloud_governance': 'Governance',
  'performance_efficiency': 'Performance',
  'security': 'Security',
  'reliability': 'Reliability',
  'sustainability': 'Sustainability',
}

function fmtCategory(cat) {
  return CAT_SHORT[cat] ?? cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function LevelCard({ label, runs, total }) {
  const covered = runs.length
  const score = avg(runs, null)
  const fidelity = avgJudge(runs)
  const pass = runs.filter(r => r.total_score >= 0.8).length

  return (
    <div className="bg-ink-900 border border-white/5 rounded-2xl p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">{label}</h2>
        <span className="text-xs font-mono text-slate-500">{covered}/{total} scenarios</span>
      </div>

      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold font-mono text-white">{fmtPct(score)}</div>
          <div className="text-xs text-slate-500 mt-1">avg score</div>
        </div>
        <div>
          <div className="text-2xl font-bold font-mono" style={{
            color: fidelity == null ? '#64748b' : fidelity >= 0.75 ? '#34d399' : fidelity >= 0.5 ? '#f5c518' : '#fb7185'
          }}>
            {fmtPct(fidelity)}
          </div>
          <div className="text-xs text-slate-500 mt-1">fidelity</div>
        </div>
        <div>
          <div className="text-2xl font-bold font-mono text-white">{pass}/{covered}</div>
          <div className="text-xs text-slate-500 mt-1">pass ≥80%</div>
        </div>
      </div>

      {/* progress bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-600 mb-1">
          <span>coverage</span>
          <span>{covered}/{total}</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div className="h-full bg-brand-blue rounded-full" style={{ width: `${(covered / total) * 100}%` }} />
        </div>
      </div>
    </div>
  )
}

function StatTile({ value, label }) {
  return (
    <div className="text-center">
      <div className="text-3xl md:text-4xl font-extrabold font-mono bg-gradient-to-r from-brand-blue via-sky-300 to-brand-green bg-clip-text text-transparent">
        {value}
      </div>
      <div className="text-xs text-slate-500 mt-1.5 tracking-wide">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [catLevel, setCatLevel] = useState('l1') // 'l1' | 'l2'

  useEffect(() => {
    fetch('/data/index.json')
      .then(r => r.json())
      .then(d => setRuns(d.runs ?? []))
      .catch(() => setRuns([]))
  }, [])

  // latest per scenario
  const latestPerScenario = Object.values(
    runs.reduce((acc, r) => {
      if (!acc[r.scenario_id] || r.timestamp > acc[r.scenario_id].timestamp)
        acc[r.scenario_id] = r
      return acc
    }, {})
  )

  const l1 = latestPerScenario.filter(r => r.scenario_id.includes('-L1-'))
  const l2 = latestPerScenario.filter(r => r.scenario_id.includes('-L2-'))

  // category breakdown — separate for L1 and L2
  function byCategory(levelRuns) {
    return Object.entries(
      levelRuns.reduce((acc, r) => {
        acc[r.category] = acc[r.category] || []
        acc[r.category].push(r)
        return acc
      }, {})
    ).sort((a, b) => avg(b[1], null) - avg(a[1], null))
  }

  const l1Cat = byCategory(l1)
  const l2Cat = byCategory(l2)
  const activeCat = catLevel === 'l1' ? l1Cat : l2Cat

  const overallScore = avg(latestPerScenario, null)
  const overallFidelity = avgJudge(latestPerScenario)
  const overallPass = latestPerScenario.filter(r => r.total_score >= 0.8).length

  return (
    <div className="space-y-8">
      {/* hero header */}
      <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-ink-900 px-8 py-9">
        <div className="absolute -top-16 -right-10 w-64 h-64 rounded-full bg-brand-blue/10 blur-3xl" />
        <div className="absolute -bottom-20 -left-10 w-64 h-64 rounded-full bg-brand-green/10 blur-3xl" />
        <div className="relative">
          <p className="text-xs font-semibold tracking-widest text-brand-yellow uppercase mb-2">Agentic CloudOps Evaluation Bench</p>
          <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
            Evaluating <span className="bg-gradient-to-r from-brand-blue to-brand-green bg-clip-text text-transparent">CloudOps agents</span> across {latestPerScenario.length} scenarios
          </h1>
        </div>

        {/* overall KPIs */}
        <div className="relative mt-8 grid grid-cols-3 gap-6 border-t border-white/5 pt-6">
          <StatTile value={fmtPct(overallScore)} label="Overall avg score" />
          <StatTile value={fmtPct(overallFidelity)} label="Judge fidelity" />
          <StatTile value={`${overallPass}/${latestPerScenario.length}`} label="Passing ≥ 80%" />
        </div>
      </div>

      {/* L1 / L2 summary */}
      <div className="grid grid-cols-2 gap-5">
        <LevelCard label="L1 — Assessment" runs={l1} total={20} />
        <LevelCard label="L2 — Planning" runs={l2} total={20} />
      </div>

      {/* category breakdown — single tabbed card */}
      <div className="bg-ink-900 border border-white/5 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Score by category</h2>
          <div className="flex gap-1 bg-white/5 rounded-lg p-1">
            {[['l1', 'L1'], ['l2', 'L2']].map(([val, label]) => (
              <button
                key={val}
                onClick={() => setCatLevel(val)}
                className={`text-xs px-3 py-1 rounded-md transition-colors ${catLevel === val ? 'bg-brand-blue text-white' : 'text-slate-500 hover:text-slate-300'
                  }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {activeCat.length === 0
          ? <p className="text-slate-600 text-xs">No runs yet.</p>
          : <div className="space-y-2.5">
            {activeCat.map(([cat, catRuns]) => (
              <ScoreBar key={cat} label={fmtCategory(cat)} score={avg(catRuns, null)} />
            ))}
          </div>
        }
      </div>

      {/* quick links */}
      <div className="flex gap-3">
        <Link to="/runs" className="text-xs text-brand-blue hover:text-sky-300 border border-white/10 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors">
          Browse all runs →
        </Link>
      </div>
    </div>
  )
}
