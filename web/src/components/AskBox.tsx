import { useState } from 'react'
import { api } from '../lib/api'

interface Answer {
  text: string
  mode: 'llm' | 'template'
  model: string | null
  grounded: boolean
  citations: { kind: string; ref: string; label: string }[]
  note?: string | null
}

const SUGGESTED = ['Is there a loan on this land?', 'Who owns this land?', 'Is there any court case?', 'What is the sale history?']

export default function AskBox({ parcelId }: { parcelId: string }) {
  const [q, setQ] = useState('')
  const [a, setA] = useState<Answer | null>(null)
  const [busy, setBusy] = useState(false)

  const ask = async (question: string) => {
    setQ(question)
    setBusy(true)
    try {
      setA(await api<Answer>('/v1/ask', { method: 'POST', body: JSON.stringify({ parcel_id: parcelId, question, language: 'en' }) }))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card p-5" data-testid="ask">
      <h3 className="font-semibold text-navy">Ask the property</h3>
      <p className="text-xs text-slate-500">Answers use only facts from the records. Every number is checked against them before it is shown.</p>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          if (q.trim()) ask(q.trim())
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Is there a loan on this land?"
          className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-navy"
        />
        <button className="btn-primary" disabled={busy}>
          {busy ? '…' : 'Ask'}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {SUGGESTED.map((s) => (
          <button key={s} onClick={() => ask(s)} className="chip bg-slate-100 text-slate-600 hover:bg-slate-200">
            {s}
          </button>
        ))}
      </div>
      {a && (
        <div className="mt-4 rounded-xl bg-paper p-4" data-testid="answer">
          <p className="text-sm leading-relaxed">{a.text}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {a.citations.slice(0, 4).map((c) => (
              <span key={c.ref} className={`chip ${c.kind === 'record' ? 'bg-blue-50 text-blue-700' : 'bg-purple-50 text-purple-700'}`}>
                {c.kind === 'record' ? '📄' : '⚑'} {c.ref}
              </span>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            {a.grounded ? '✓ Grounded in records' : 'Not grounded'} · {a.mode === 'llm' ? `phrased by ${a.model}` : 'template answer from SQL facts'} · not legal advice
          </p>
        </div>
      )}
    </div>
  )
}
