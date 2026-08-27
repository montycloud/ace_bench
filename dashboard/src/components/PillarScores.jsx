import ScoreBar from './ScoreBar'

const PILLARS = ['tools', 'answer', 'reasoning', 'safety']
const LABELS  = { tools: 'Tools', answer: 'Answer', reasoning: 'Reasoning', safety: 'Safety' }

export default function PillarScores({ scores }) {
  return (
    <div className="flex flex-col gap-3">
      {PILLARS.map(p => (
        <ScoreBar key={p} label={LABELS[p]} score={scores[p] ?? 0} />
      ))}
    </div>
  )
}
