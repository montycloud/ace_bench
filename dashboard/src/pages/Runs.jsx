import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ScoreChip from '../components/ScoreChip'
import PromptModal from '../components/PromptModal'

const PILLARS = ['tools', 'answer', 'safety']

function fmtCategory(cat) {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const REPORT_GENERATE_TEMPLATE = `You are analysing multiple evaluation runs of a CloudOps AI agent on a specific scenario. Produce a comprehensive scenario-level report.

## Scenario
Name: {scenario.get('scenario', '')}
Category: {scenario.get('category', '')}
WAFR Pillar: {scenario.get('wafr_pillar', '')}

## Success Criteria
{scenario.get('success_criteria', '(not specified)')}

## Hard-Fail Conditions
{scenario.get('hard_fail', '(none specified)')}

## Evaluation Criteria
{criteria_str}

## All Judged Runs ({len(runs)} runs)

{runs_str}

---

Be specific — reference run IDs when calling out notable instances. Identify patterns, not just individual failures.

Return a single valid JSON object with no markdown fences:
{
  "summary": "...",
  "criterion_breakdown": [...],
  "recurring_failures": "...",
  "trends": "...",
  "recommendations": "...",
  "what_changed": null
}`

const REPORT_UPDATE_TEMPLATE = `You are updating an existing scenario-level report for a CloudOps AI agent with new evaluation runs.

## Scenario
Name: {scenario.get('scenario', '')}
...

## Existing Report (covers previous runs)
{existing_report_json}

## New Runs ({len(new_runs)} new)
{new_runs_str}

---

Rewrite the full report incorporating all runs. Fill in "what_changed" with what the new runs revealed — improvements, regressions, new patterns, or confirmation of existing ones.`

function safeId(scenarioId) {
  return scenarioId.replace(/-/g, '_')
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className="text-xs px-2 py-0.5 rounded-md border border-white/10 bg-white/5 text-slate-400 hover:text-slate-200 transition-colors"
    >
      {copied ? 'copied' : 'copy'}
    </button>
  )
}

function ReportPanel({ scenarioId, judgedRunIds }) {
  const [report, setReport] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [showPrompt, setShowPrompt] = useState(false)

  useEffect(() => {
    setReport(null)
    setNotFound(false)
    fetch(`/data/reports/${safeId(scenarioId)}.json`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setReport)
      .catch(() => setNotFound(true))
  }, [scenarioId])

  const cmd = `python -m sandbox.report ${scenarioId}`

  // detect stale: judged runs not in report
  const includedIds = new Set(report?.run_ids_included ?? [])
  const newRunCount = judgedRunIds.filter(id => !includedIds.has(id)).length
  const isStale = report && newRunCount > 0

  return (
    <>
      {showPrompt && (
        <PromptModal
          title={`Report Prompt (${report?.prompt_type ?? 'generate'})`}
          prompt={report?.prompt ?? (report?.prompt_type === 'update' ? REPORT_UPDATE_TEMPLATE : REPORT_GENERATE_TEMPLATE)}
          onClose={() => setShowPrompt(false)}
        />
      )}
      <div className="bg-ink-900 border border-white/5 rounded-2xl overflow-hidden">
        <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Scenario Report</h3>
          <div className="flex items-center gap-3">
            {report && (
              <button onClick={() => setShowPrompt(true)}
                className="text-xs text-slate-500 hover:text-slate-300 border border-white/10 px-2 py-1 rounded-md hover:bg-white/5 transition-colors">
                view prompt
              </button>
            )}
            {report && (
              <span className="text-xs text-slate-600">
                {report.total_runs} runs · updated {report.updated_at?.slice(0, 10)}
              </span>
            )}
          </div>
        </div>

        <div className="p-5 space-y-4">
          {/* stale / missing notice */}
          {(notFound || isStale) && (
            <div className={`rounded-lg border p-3 ${notFound ? 'border-white/10 bg-white/5' : 'border-brand-yellow/30 bg-brand-yellow/5'}`}>
              <p className="text-xs text-slate-400 mb-2">
                {notFound
                  ? 'No report yet.'
                  : `${newRunCount} new judged run${newRunCount > 1 ? 's' : ''} not included in last report.`
                }
                {' '}Run to {notFound ? 'generate' : 'update'}:
              </p>
              <div className="flex items-center gap-2">
                <code className="text-xs font-mono text-slate-300 bg-white/5 px-2 py-1 rounded flex-1">{cmd}</code>
                <CopyButton text={cmd} />
              </div>
            </div>
          )}

          {!report && !notFound && (
            <p className="text-xs text-slate-600">Loading…</p>
          )}

          {report && (
            <div className="space-y-5">
              {/* summary */}
              <p className="text-sm text-slate-300 leading-relaxed">{report.summary}</p>

              {/* criterion breakdown */}
              {(report.criterion_breakdown ?? []).length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-3">Criterion Breakdown</p>
                  <div className="space-y-3">
                    {report.criterion_breakdown.map((cb, i) => {
                      const met = cb.met_count ?? 0
                      const total = met + (cb.not_met_count ?? 0)
                      const color = met === total ? 'text-emerald-400' : met === 0 ? 'text-red-400' : 'text-yellow-400'
                      return (
                        <div key={i} className="border border-slate-800 rounded-lg p-3">
                          <div className="flex items-start gap-3 mb-1.5">
                            <span className={`shrink-0 font-mono text-sm font-bold ${color}`}>{met}/{total}</span>
                            <p className="text-xs text-slate-200">{cb.criterion}</p>
                          </div>
                          <p className="text-xs text-slate-500 leading-relaxed pl-8">{cb.analysis}</p>
                          {(cb.notable_run_ids ?? []).length > 0 && (
                            <div className="pl-8 mt-1.5 flex flex-wrap gap-1">
                              {cb.notable_run_ids.map(rid => (
                                <Link key={rid} to={`/runs/${rid}`}
                                  className="text-xs font-mono text-brand-blue hover:text-sky-300 underline underline-offset-2">
                                  {rid.slice(-19)}
                                </Link>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* recurring failures / trends / recommendations / what changed */}
              {[
                ['recurring_failures', 'Recurring Failures'],
                ['trends', 'Trends'],
                ['recommendations', 'Recommendations'],
                ['what_changed', 'What Changed'],
              ].map(([key, label]) => report[key] ? (
                <div key={key}>
                  <p className="text-xs text-slate-500 uppercase tracking-wide mb-1.5">{label}</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{report[key]}</p>
                </div>
              ) : null)}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default function Runs() {
  const [runs, setRuns] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [levelFilter, setLevelFilter] = useState('all') // 'all' | 'l1' | 'l2'

  useEffect(() => {
    fetch('/data/index.json')
      .then(r => r.json())
      .then(d => {
        const all = d.runs ?? []
        setRuns(all)
        if (all.length) {
          const sorted = [...all].sort((a, b) => b.timestamp.localeCompare(a.timestamp))
          setSelectedId(sorted[0].scenario_id)
        }
      })
      .catch(() => setRuns([]))
  }, [])

  const allLatestPerScenario = Object.values(
    runs.reduce((acc, r) => {
      if (!acc[r.scenario_id] || r.timestamp > acc[r.scenario_id].timestamp)
        acc[r.scenario_id] = r
      return acc
    }, {})
  ).sort((a, b) => (a.scenario_name ?? a.scenario_id).localeCompare(b.scenario_name ?? b.scenario_id))

  const latestPerScenario = allLatestPerScenario.filter(r => {
    if (levelFilter === 'l1') return r.scenario_id.includes('-L1-')
    if (levelFilter === 'l2') return r.scenario_id.includes('-L2-')
    return true
  })

  const byCategory = latestPerScenario.reduce((acc, r) => {
    acc[r.category] = acc[r.category] || []
    acc[r.category].push(r)
    return acc
  }, {})

  const selectedRuns = [...runs]
    .filter(r => r.scenario_id === selectedId)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))

  const judgedRunIds = selectedRuns.filter(r => r.has_judge).map(r => r.id)

  const selected = latestPerScenario.find(r => r.scenario_id === selectedId)

  return (
    <div className="flex -mx-6 -my-8" style={{ height: 'calc(100vh - 57px)' }}>

      {/* left sidebar */}
      <div className="w-72 shrink-0 border-r border-white/5 overflow-y-auto">
        {/* level filter */}
        <div className="flex gap-1 p-2 border-b border-white/5 sticky top-0 bg-ink-950/95 backdrop-blur z-10">
          {[['all', 'All'], ['l1', 'L1'], ['l2', 'L2']].map(([val, label]) => (
            <button
              key={val}
              onClick={() => { setLevelFilter(val); setSelectedId(null) }}
              className={`flex-1 text-xs py-1 rounded-md transition-colors ${levelFilter === val
                  ? 'bg-brand-blue text-white'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                }`}
            >
              {label}
            </button>
          ))}
        </div>
        {Object.entries(byCategory).sort().map(([cat, scenarios]) => (
          <div key={cat}>
            <div className="px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider bg-ink-900/80 sticky top-0 border-b border-white/5">
              {fmtCategory(cat)}
            </div>
            {scenarios.map(s => (
              <button
                key={s.scenario_id}
                onClick={() => setSelectedId(s.scenario_id)}
                className={`w-full text-left px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors flex items-start justify-between gap-3 ${selectedId === s.scenario_id
                    ? 'bg-white/5 border-l-2 border-l-brand-blue pl-[14px]'
                    : ''
                  }`}
              >
                <span className={`text-xs leading-snug ${selectedId === s.scenario_id ? 'text-white' : 'text-slate-400'}`}>
                  {s.scenario_name ?? s.scenario_id}
                </span>
                <div className="shrink-0 mt-0.5">
                  <ScoreChip score={s.total_score} />
                </div>
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* right panel */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {!selected ? (
          <p className="text-slate-500 text-sm">Select a scenario from the left.</p>
        ) : (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-bold text-white">{selected.scenario_name ?? selected.scenario_id}</h2>
              <p className="text-xs font-mono text-slate-500 mt-0.5">{selected.scenario_id}</p>
              <p className="text-xs text-slate-500 mt-1">
                {selectedRuns.length} run{selectedRuns.length !== 1 ? 's' : ''}
                {judgedRunIds.length > 0 && ` · ${judgedRunIds.length} judged`}
              </p>
            </div>

            {/* runs table */}
            <div className="bg-ink-900 border border-white/5 rounded-2xl overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-white/5 bg-white/[0.02]">
                    <th className="text-left px-4 py-3 font-normal">Date</th>
                    <th className="text-left px-4 py-3 font-normal">Model</th>
                    {PILLARS.map(p => (
                      <th key={p} className="text-right px-3 py-3 font-normal capitalize">{p}</th>
                    ))}
                    <th className="text-right px-3 py-3 font-normal">Total</th>
                    <th className="text-right px-4 py-3 font-normal text-slate-500">Judge</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedRuns.map((r, i) => (
                    <tr key={r.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3">
                        <Link to={`/runs/${r.id}`} className="text-brand-blue hover:text-sky-300">
                          {new Date(r.timestamp).toLocaleString()}
                        </Link>
                        {i === 0 && <span className="ml-2 text-xs text-slate-600">latest</span>}
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono">{r.model ?? '—'}</td>
                      {PILLARS.map(p => (
                        <td key={p} className="px-3 py-3 text-right">
                          <ScoreChip score={r.scores?.[p] ?? 0} />
                        </td>
                      ))}
                      <td className="px-3 py-3 text-right">
                        <ScoreChip score={r.total_score} />
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs">
                        {r.has_judge
                          ? <span className={r.judge_met === r.judge_total ? 'text-emerald-400' : r.judge_met > 0 ? 'text-yellow-400' : 'text-red-400'}>
                            {r.judge_met}/{r.judge_total}
                          </span>
                          : <span className="text-slate-700">—</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* scenario report */}
            {judgedRunIds.length > 0 && (
              <ReportPanel scenarioId={selectedId} judgedRunIds={judgedRunIds} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
