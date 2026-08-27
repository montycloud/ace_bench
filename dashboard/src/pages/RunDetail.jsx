import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import ScoreChip from '../components/ScoreChip'
import ScoreBar from '../components/ScoreBar'
import PromptModal from '../components/PromptModal'

const INNER_TOOLS = new Set(['execute', 'memory', 'extract_tool_schemas'])
const KNOWN_AGENTS = new Set(['toolloop', 's3soa', 'soa', 'eoa', 'poa'])

// Run ids look like `{scenario}__{agent}__{timestamp}` (agent-scoped storage under
// runner/result/{agent}/). Ids without a recognized agent segment fall back to 'toolloop'.
function runAgentFromId(id) {
  const parts = id.split('__')
  const candidate = parts[parts.length - 2]
  return KNOWN_AGENTS.has(candidate) ? candidate : 'toolloop'
}

function tcInputSummary(tool, rawInput) {
  try {
    const inp = JSON.parse(rawInput)
    if (tool === 'analyst') {
      const q = (inp.query ?? '').split('\n')[0].replace(/^USER REQUEST:\s*/i, '').trim()
      return q.length > 120 ? q.slice(0, 120) + '…' : q
    }
    if (tool === 'execute') return 'Python script execution'
    if (tool === 'memory') {
      const parts = [inp.action]
      if (inp.data_type) parts.push(inp.data_type)
      return parts.join(' · ')
    }
    if (tool === 'extract_tool_schemas') {
      const names = (inp.tool_names ?? []).join(', ')
      return `schemas for: ${names.length > 80 ? names.slice(0, 80) + '…' : names}`
    }
    if (tool === 'get_findings_summary') {
      const parts = []
      if (inp.dimension) parts.push(inp.dimension)
      if (inp.summary_type) parts.push(inp.summary_type)
      if (inp.pillar_id) parts.push(`pillar=${inp.pillar_id}`)
      return parts.join(' / ') || 'get findings summary'
    }
    if (tool === 'list_assessment_top_entities') {
      return `top ${inp.page_size ?? '?'} ${inp.entity_type ?? 'entities'}`
    }
    if (tool === 'list_assessment_resources') {
      return `list resources (page_size=${inp.page_size ?? '?'})`
    }
    if (tool === 'get_assessment') return 'fetch WAFR assessment'
    if (tool === 'get_tenant') return 'fetch tenant metadata'
    if (tool === 'get_saving_opportunities') return 'fetch savings opportunities'
    // fallback: first key=value pair
    const first = Object.entries(inp)[0]
    return first ? `${first[0]}=${JSON.stringify(first[1])}` : ''
  } catch { return '' }
}

function tcOutputSummary(output) {
  if (!output) return ''
  const s = String(output).trim()
  // Analyst step-completion message
  if (s.startsWith('✓')) return s.split('\n')[0].slice(0, 100)
  // JSON error
  try {
    const p = JSON.parse(s)
    if (p?.status === 'error') return `error: ${p.message ?? 'MCP tool failed'}`
    if (p?.status === 'success') return 'success'
  } catch { }
  return s.slice(0, 100).replace(/\n/g, ' ')
}

function TimelineStep({ index, tc }) {
  const [open, setOpen] = useState(false)
  const isInner = INNER_TOOLS.has(tc.tool)
  const summary = tcInputSummary(tc.tool, tc.input)
  const outSummary = tcOutputSummary(tc.output)
  const isError = outSummary.startsWith('error:')

  const dotColor = isInner
    ? 'bg-white/5 text-slate-500'
    : tc.tool === 'analyst'
      ? 'bg-brand-blue/15 text-brand-blue'
      : 'bg-sky-900/40 text-sky-400'

  const nameColor = isInner ? 'text-slate-500' : tc.tool === 'analyst' ? 'text-brand-blue' : 'text-sky-300'

  return (
    <div className={`relative flex gap-3 ${isInner ? 'opacity-60' : ''}`}>
      {/* connector */}
      <div className="flex flex-col items-center">
        <div className={`flex-none w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${dotColor}`}>
          {index + 1}
        </div>
        <div className="w-px flex-1 bg-slate-800 mt-1" />
      </div>
      {/* content */}
      <div className="pb-4 min-w-0 flex-1">
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full text-left group"
        >
          <div className="flex items-center gap-2">
            <span className={`text-xs font-mono font-semibold ${nameColor}`}>{tc.tool}</span>
            <span className="text-xs text-slate-600 group-hover:text-slate-400 transition-colors">{open ? '▲' : '▼'}</span>
          </div>
          {summary && <p className="text-xs text-slate-500 mt-0.5 truncate">{summary}</p>}
          {outSummary && (
            <p className={`text-xs mt-0.5 truncate ${isError ? 'text-red-500' : outSummary.startsWith('✓') ? 'text-emerald-500' : 'text-slate-600'}`}>
              {outSummary}
            </p>
          )}
        </button>
        {open && (
          <div className="mt-2 space-y-2">
            {tc.input && (() => {
              try {
                const inp = JSON.parse(tc.input)
                if (tc.tool === 'execute' && inp.code) return (
                  <div>
                    <p className="text-[10px] text-slate-600 uppercase tracking-wide mb-1">Code</p>
                    <pre className="text-[11px] text-slate-400 bg-white/5 rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-64">
                      {inp.code}
                    </pre>
                  </div>
                )
                return (
                  <div>
                    <p className="text-[10px] text-slate-600 uppercase tracking-wide mb-1">Input</p>
                    <pre className="text-[11px] text-slate-400 bg-white/5 rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-40">
                      {JSON.stringify(inp, null, 2)}
                    </pre>
                  </div>
                )
              } catch { return null }
            })()}
            {tc.output && (
              <div>
                <p className="text-[10px] text-slate-600 uppercase tracking-wide mb-1">Output</p>
                <pre className="text-[11px] text-slate-400 bg-white/5 rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-48">
                  {(() => {
                    const s = String(tc.output)
                    try {
                      const p = JSON.parse(s)
                      // Only pretty-print if it's actually an object/array
                      if (typeof p === 'object' && p !== null) return JSON.stringify(p, null, 2)
                    } catch { }
                    return s
                  })()}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ title, children, flush = false }) {
  return (
    <div className="bg-ink-900 border border-white/5 rounded-2xl overflow-hidden">
      <div className="px-5 py-3 border-b border-white/5">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</h2>
      </div>
      <div className={flush ? '' : 'p-5'}>{children}</div>
    </div>
  )
}

function Tag({ label, color = 'slate' }) {
  const colors = {
    green: 'bg-emerald-900/50 text-emerald-400 border-emerald-800',
    red: 'bg-red-900/50 text-red-400 border-red-800',
    slate: 'bg-white/5 text-slate-400 border-white/10',
    yellow: 'bg-brand-yellow/10 text-brand-yellow border-brand-yellow/30',
    violet: 'bg-brand-blue/10 text-brand-blue border-brand-blue/30',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-mono ${colors[color]}`}>
      {label}
    </span>
  )
}

const JUDGE_PROMPT_TEMPLATE = `You are evaluating a CloudOps AI agent on a compliance assessment scenario. Analyse the quality of the agent's investigation and response.

## Scenario
Name: {scenario.get('scenario', '')}
Category: {scenario.get('category', '')}
WAFR Pillar: {scenario.get('wafr_pillar', '')}

## What Success Looks Like
{scenario.get('success_criteria', '(not specified)')}

## Hard-Fail Conditions
{scenario.get('hard_fail', '(none specified)')}

## Known Correct Resources (ground truth confirmed in WAFR assessment)
{resources_str}

## Resources That Should NOT Be Flagged
{should_not_str}

---

## Agent's Tool Calls and Full Outputs
{tool_calls_str}

---

## Agent's Final Response
{response}

---

## Evaluation Instructions

For each criterion below, write a concise factual finding that describes exactly what the agent did or did not do — citing specific evidence from the tool calls or response above. Do not speculate.

Important:
- If tools structurally cannot surface specific resource IDs (returning type summaries or aggregate counts), credit the agent for explicitly acknowledging that rather than penalising it.
- If the agent invents resource names, check IDs, or configuration details not present in tool output, say so explicitly in the finding.

Criteria:
{criteria_numbered}

Return a single valid JSON object with no markdown fences:
{
  "criteria_results": [
    {
      "criterion": "(copy the criterion text exactly as written above)",
      "met": true,
      "finding": "one to two sentences of factual observation citing specific evidence from the tool output or the agent's response"
    }
  ],
  "overall_comment": "two to three sentences: what the agent got right, what it missed, and the primary failure mode if any"
}`

function JudgeSection({ judge }) {
  const [showPrompt, setShowPrompt] = useState(false)

  if (!judge) return null
  if (judge.error) return (
    <Section title="LLM Judge">
      <p className="text-xs text-red-400">{judge.error}</p>
    </Section>
  )

  const met = judge.met ?? judge.criteria_results?.filter(r => r.met).length ?? 0
  const total = judge.total ?? judge.criteria_results?.length ?? 0
  return (
    <>
      {showPrompt && (
        <PromptModal title="Judge Prompt" prompt={judge.prompt ?? JUDGE_PROMPT_TEMPLATE} onClose={() => setShowPrompt(false)} />
      )}
      <Section title={`LLM Judge · ${judge.judge_model ?? ''}`}>
        {/* score summary + prompt link */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className={`text-2xl font-bold font-mono ${met === total ? 'text-emerald-400' : met > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
              {met}/{total}
            </span>
            <span className="text-sm text-slate-500">criteria met</span>
          </div>
          <button onClick={() => setShowPrompt(true)}
            className="text-xs text-slate-500 hover:text-slate-300 border border-white/10 px-2 py-1 rounded-md hover:bg-white/5 transition-colors">
            view prompt
          </button>
        </div>

        {/* overall comment */}
        {judge.overall_comment && (
          <p className="text-sm text-slate-300 leading-relaxed mb-5">{judge.overall_comment}</p>
        )}

        {/* per-criterion findings */}
        <div className="space-y-4">
          {(judge.criteria_results ?? []).map((r, i) => (
            <div key={i} className={`border rounded-lg p-3 ${r.met ? 'border-white/10' : 'border-red-900/50 bg-red-900/5'}`}>
              <p className="text-xs font-medium text-slate-200 leading-relaxed mb-1.5">
                <span className="text-slate-500 font-mono mr-1.5">{i + 1}.</span>
                {r.criterion}
              </p>
              {r.finding && (
                <p className="text-xs text-slate-400 leading-relaxed pl-5 italic">{r.finding}</p>
              )}
            </div>
          ))}
        </div>
      </Section>
    </>
  )
}

function PillarRow({ label, score, children }) {
  return (
    <div>
      <ScoreBar label={label} score={score} />
      {children && <div className="mt-2 ml-[92px] space-y-1">{children}</div>}
    </div>
  )
}

function ToolRow({ icon, tool, params, reason, faded = false }) {
  const hasParams = params && Object.keys(params).length > 0
  return (
    <div className={`flex items-start gap-2 text-xs ${faded ? 'opacity-50' : ''}`}>
      <span className={`shrink-0 font-bold ${icon === '✓' ? 'text-emerald-500' : 'text-red-500'}`}>{icon}</span>
      <div className="min-w-0">
        <span className="font-mono text-slate-200">{tool}</span>
        {hasParams && (
          <span className="font-mono text-slate-500 ml-2">{JSON.stringify(params)}</span>
        )}
        {reason && (
          <p className="text-slate-500 italic mt-0.5">{reason}</p>
        )}
      </div>
    </div>
  )
}

export default function RunDetail() {
  const { id } = useParams()
  const [run, setRun] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch(`/data/results/${runAgentFromId(id)}/${id}.json`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setRun)
      .catch(() => setError(true))
  }, [id])

  if (error) return <div className="text-red-400 text-sm">Run not found: {id}</div>
  if (!run) return <div className="text-slate-500 text-sm">Loading…</div>

  const details = run.details ?? {}
  const answer = details.answer ?? {}
  const tools = details.tools ?? {}
  const safety = details.safety ?? {}
  const fidelity = details.fidelity ?? {}
  const output = details.output ?? {}

  const foundSet = new Set(answer.found ?? [])
  const fpSet = new Set(safety.false_positives ?? [])

  return (
    <div className="space-y-5">

      {/* header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link to="/runs" className="text-slate-500 text-xs hover:text-slate-300">← All runs</Link>
          <h1 className="text-xl font-bold text-white mt-1 leading-snug">
            {run.scenario_name ?? run.scenario_id}
          </h1>
          <p className="text-xs font-mono text-slate-500 mt-0.5">{run.scenario_id}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-slate-500 text-xs">{new Date(run.timestamp).toLocaleString()}</span>
            {run.model && (
              <span className="text-xs font-mono px-2 py-0.5 rounded border border-white/10 bg-white/5 text-slate-400">
                {run.model}
              </span>
            )}
            {run.token_usage?.total && (
              <span className="text-xs text-slate-600">
                {run.token_usage.total.toLocaleString()} tokens
              </span>
            )}
          </div>
        </div>
        <ScoreChip score={run.total_score} size="lg" />
      </div>

      {/* scenario overview */}
      {run.scenario && (
        <Section title="Scenario">
          {run.scenario.description && (
            <p className="text-sm text-slate-300 leading-relaxed mb-4">
              {run.scenario.description}
            </p>
          )}
          {run.scenario.objective && (
            <div className="bg-slate-800/50 rounded p-3">
              <p className="text-xs text-slate-500 mb-1 uppercase tracking-wide">Objective sent to agent</p>
              <p className="text-xs text-slate-400 font-mono leading-relaxed">
                {run.scenario.objective.split('|')[0].trim()}
              </p>
            </div>
          )}
        </Section>
      )}

      {/* pillar scores */}
      <Section title="Scores">
        <div className="grid grid-cols-5 gap-4 text-center">
          {['tools', 'answer', 'safety', 'output'].map(p => (
            <div key={p}>
              <div className="text-2xl font-bold font-mono" style={{
                color: (run.scores[p] ?? 0) >= 0.8 ? '#34d399' : (run.scores[p] ?? 0) >= 0.5 ? '#f5c518' : '#fb7185'
              }}>
                {Math.round((run.scores[p] ?? 0) * 100)}%
              </div>
              <div className="text-xs text-slate-500 capitalize mt-1">{p}</div>
            </div>
          ))}
          {/* fidelity from LLM judge */}
          <div>
            {run.judge && !run.judge.error ? (() => {
              const met = run.judge.met ?? 0
              const total = run.judge.total ?? 0
              const score = total ? met / total : null
              return (
                <>
                  <div className="text-2xl font-bold font-mono" style={{
                    color: score == null ? '#64748b' : score >= 0.75 ? '#34d399' : score >= 0.5 ? '#fbbf24' : '#f87171'
                  }}>
                    {score == null ? '—' : `${met}/${total}`}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">fidelity</div>
                </>
              )
            })() : (
              <>
                <div className="text-2xl font-bold font-mono text-slate-700">—</div>
                <div className="text-xs text-slate-500 mt-1">fidelity</div>
              </>
            )}
          </div>
        </div>
      </Section>

      {/* LLM judge */}
      <JudgeSection judge={run.judge} />

      {/* investigation */}
      <div className="grid grid-cols-2 gap-5">

        {/* expected vs found tools */}
        <Section title="Expected tool calls">
          <div className="space-y-3">
            <p className="text-xs text-slate-600 italic">What the gold label expects the agent to call and why</p>
            {(tools.expected_tool_calls ?? []).length === 0
              ? <p className="text-slate-600 text-xs">No expected tool calls defined.</p>
              : (tools.expected_tool_calls ?? []).map((t, i) => (
                <ToolRow
                  key={i}
                  icon={tools.found_tool_calls?.find(f => f.tool === t.tool) ? '✓' : '✗'}
                  tool={t.tool}
                  params={t.params}
                  reason={t.reason}
                />
              ))
            }
          </div>
        </Section>

        {/* actual tool call summary */}
        <Section title={`Actual tool calls (${run.tool_calls?.length ?? 0})`}>
          {(run.tool_calls ?? []).length === 0
            ? <p className="text-slate-600 text-xs">No tool calls captured.</p>
            : <div className="flex flex-wrap gap-1.5">
              {Object.entries(
                (run.tool_calls ?? []).reduce((acc, tc) => {
                  acc[tc.tool] = (acc[tc.tool] ?? 0) + 1
                  return acc
                }, {})
              ).sort((a, b) => b[1] - a[1]).map(([tool, count]) => {
                const isInner = INNER_TOOLS.has(tool)
                return (
                  <span key={tool} className={`text-xs px-2 py-0.5 rounded border font-mono ${isInner
                      ? 'bg-white/5 text-slate-500 border-white/10'
                      : tool === 'analyst'
                        ? 'bg-brand-blue/10 text-brand-blue border-brand-blue/30'
                        : 'bg-sky-900/30 text-sky-400 border-sky-800'
                    }`}>
                    {tool} {count > 1 && <span className="opacity-60">×{count}</span>}
                  </span>
                )
              })}
            </div>
          }
        </Section>
      </div>

      {/* investigation timeline */}
      {(run.tool_calls ?? []).length > 0 && (
        <Section title="Investigation walkthrough">
          <p className="text-xs text-slate-600 mb-4 italic">
            Click any step to expand full input / output.
            <span className="ml-3 inline-flex gap-2">
              <span className="text-violet-400">analyst</span>
              <span className="text-sky-400">MCP tools</span>
              <span className="text-slate-500">internal</span>
            </span>
          </p>
          <div className="max-h-[600px] overflow-y-auto pr-2">
            {run.tool_calls.map((tc, i) => (
              <TimelineStep key={i} index={i} tc={tc} />
            ))}
            {/* last item has no trailing line */}
          </div>
        </Section>
      )}

      {/* resources */}
      <Section title="Resources">
        <div className="space-y-5">

          {/* correct resources with found/missed status */}
          {(answer.correct_resources ?? []).length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-2">Expected resources</p>
              <div className="space-y-1.5">
                {answer.correct_resources.map(r => {
                  const inResponse = (answer.found_in_response ?? []).includes(r)
                  const inTools = (answer.found_in_tools ?? []).includes(r)
                  const found = foundSet.has(r)
                  return (
                    <div key={r} className="flex items-center gap-3 text-xs">
                      <span className={`shrink-0 font-bold ${found ? 'text-emerald-500' : 'text-red-500'}`}>
                        {found ? '✓' : '✗'}
                      </span>
                      <span className="font-mono text-slate-300">{r}</span>
                      {found && (
                        <span className="text-slate-600">
                          found in {inResponse && inTools ? 'response + tools' : inResponse ? 'response' : 'tools'}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            {/* unconfirmed */}
            {(answer.unconfirmed ?? []).length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-2">Unconfirmed <span className="text-slate-600">(in output, not classified)</span></p>
                <div className="flex flex-wrap gap-1.5">
                  {answer.unconfirmed.map(r => <Tag key={r} label={r} color="violet" />)}
                </div>
              </div>
            )}

            {/* should not flag */}
            {(safety.should_not_flag ?? []).length > 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-2">Should not flag</p>
                <div className="flex flex-wrap gap-1.5">
                  {safety.should_not_flag.map(r => (
                    <Tag key={r} label={r} color={fpSet.has(r) ? 'red' : 'slate'} />
                  ))}
                </div>
              </div>
            )}

            {/* output validity */}
            <div>
              <p className="text-xs text-slate-500 mb-2">Output format</p>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs">
                  <span className={output.valid_json ? 'text-emerald-500' : 'text-red-500'}>
                    {output.valid_json ? '✓' : '✗'}
                  </span>
                  <span className="text-slate-400">Valid JSON</span>
                </div>
                {(output.issues ?? []).map((issue, i) => (
                  <p key={i} className="text-xs text-red-400 ml-4">{issue}</p>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* judge criteria (from gold label, for reference) */}
      {(run.scenario?.judge_criteria ?? []).length > 0 && !run.judge && (
        <Section title="Judge criteria (not yet evaluated)">
          <div className="space-y-2">
            {run.scenario.judge_criteria.map((c, i) => (
              <div key={i} className="flex gap-2 text-xs">
                <span className="shrink-0 text-slate-600 font-mono">{i + 1}.</span>
                <span className="text-slate-400">{c}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-600 mt-3 italic">
            Run <code className="font-mono">python -m runner.run --rejudge</code> to score these.
          </p>
        </Section>
      )}

      {/* agent response */}
      <Section title="Agent response">
        <div className="prose prose-invert prose-xs max-w-none max-h-96 overflow-y-auto text-xs
          prose-headings:text-slate-200 prose-headings:font-semibold prose-headings:text-sm
          prose-p:text-slate-300 prose-p:leading-relaxed prose-p:text-xs
          prose-li:text-slate-300 prose-li:text-xs prose-strong:text-slate-200
          prose-code:text-sky-300 prose-code:bg-slate-800 prose-code:px-1 prose-code:rounded prose-code:text-xs
          prose-pre:bg-slate-800 prose-pre:text-slate-300 prose-pre:text-xs">
          <ReactMarkdown>{run.response}</ReactMarkdown>
        </div>
      </Section>

    </div>
  )
}
