import { useEffect } from 'react'

export default function PromptModal({ title, prompt, onClose }) {
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-ink-900 border border-white/10 rounded-2xl w-[80vw] max-w-4xl max-h-[80vh] flex flex-col shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 shrink-0">
          <h2 className="text-sm font-semibold text-slate-300">{title}</h2>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 text-xs px-2 py-1 rounded-md hover:bg-white/5 transition-colors"
          >
            close
          </button>
        </div>
        {/* body */}
        <pre className="flex-1 overflow-y-auto p-5 text-xs text-slate-400 font-mono leading-relaxed whitespace-pre-wrap">
          {prompt}
        </pre>
      </div>
    </div>
  )
}
