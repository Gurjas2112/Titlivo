import { useState } from 'react'
import type { ChainEvent, Flag, Person, Severity } from '../lib/api'
import { API, fmtDate, inr } from '../lib/api'
import type { PassportStatus } from '../lib/verifyPassport'

export function SeverityChip({ s }: { s: Severity }) {
  const cls = { high: 'bg-danger-soft text-danger', medium: 'bg-saffron-soft text-saffron', info: 'bg-slate-100 text-slate-600' }[s]
  return <span className={`chip ${cls}`}>{s === 'high' ? '▲ High' : s === 'medium' ? '● Medium' : 'Info'}</span>
}

const STATUS_STYLE: Record<PassportStatus, { cls: string; icon: string; label: string }> = {
  LIVE: { cls: 'bg-mint text-white', icon: '✓', label: 'LIVE' },
  SUSPENDED: { cls: 'bg-saffron text-white', icon: '⏸', label: 'SUSPENDED' },
  REVOKED: { cls: 'bg-danger text-white', icon: '✕', label: 'REVOKED' },
  EXPIRED: { cls: 'bg-slate-500 text-white', icon: '⌛', label: 'EXPIRED' },
  INVALID_SIGNATURE: { cls: 'bg-danger text-white', icon: '✕', label: 'INVALID SIGNATURE' },
  UNVERIFIED: { cls: 'bg-slate-500 text-white', icon: '?', label: 'UNVERIFIED' },
}

export function StatusPill({ status, big = false }: { status: PassportStatus; big?: boolean }) {
  const s = STATUS_STYLE[status]
  return (
    <span
      data-testid="status-pill"
      data-status={status}
      className={`inline-flex items-center gap-2 rounded-full font-bold tracking-wide ${s.cls} ${big ? 'px-6 py-3 text-2xl' : 'px-3 py-1 text-sm'}`}
    >
      <span aria-hidden>{s.icon}</span>
      {s.label}
    </span>
  )
}

export function FlagCard({ f }: { f: Flag }) {
  const [open, setOpen] = useState(false)
  const sentinel = f.title.startsWith('Fraud Sentinel')
  return (
    <div
      className={`rounded-xl border p-4 ${f.severity === 'high' ? 'border-danger/30 bg-danger-soft/40' : 'border-amber/40 bg-saffron-soft/40'}`}
      data-testid={`flag-${f.id}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs font-semibold text-slate-500">{f.id}</span>
        <SeverityChip s={f.severity} />
        {sentinel && <span className="chip bg-navy text-white">Fraud Sentinel</span>}
        <h4 className="font-semibold">{f.title.replace('Fraud Sentinel: ', '')}</h4>
      </div>
      <p className="mt-2 text-sm leading-relaxed">{f.text}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span className="chip bg-blue-50 text-blue-700" title="Source record">
          📄 {f.source_record_id}
        </span>
        <span>Rule: {f.basis}</span>
        <button className="underline" onClick={() => setOpen(!open)}>
          {open ? 'Hide' : 'Show'} evidence
        </button>
      </div>
      {open && <pre className="mt-2 overflow-x-auto rounded-lg bg-white p-3 font-mono text-xs">{JSON.stringify(f.evidence, null, 2)}</pre>}
    </div>
  )
}

const names = (ps: Person[]) => ps.map((p) => p.name).join(', ') || '—'
const TYPE_COLOR: Record<string, string> = {
  grant: 'bg-slate-500',
  sale: 'bg-navy',
  succession: 'bg-mint',
  gift: 'bg-blue-500',
  partition: 'bg-purple-500',
  gpa: 'bg-amber',
}

export function Timeline({ events, lang }: { events: ChainEvent[]; lang: string }) {
  return (
    <ol className="relative ml-3 border-l-2 border-slate-200" data-testid="timeline">
      {events.map((e) => (
        <li key={e.position} className="mb-4 ml-5">
          <span
            className={`absolute -left-[9px] mt-1.5 h-4 w-4 rounded-full ring-4 ring-white ${e.consistent ? TYPE_COLOR[e.event_type] ?? 'bg-slate-400' : 'bg-danger'}`}
          />
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span className="text-sm font-semibold capitalize">{e.event_type}</span>
            <span lang={lang} className="text-sm text-slate-500">
              {e.native_term}
            </span>
            <span className="text-xs text-slate-500">· {fmtDate(e.registered_on)}</span>
            <span className="font-mono text-xs text-slate-400">entry {e.mutation_no}</span>
            {!e.consistent && <span className="chip bg-danger text-white">chain break</span>}
            {e.injected && <span className="chip bg-saffron text-white">new event</span>}
            {e.event_type === 'succession' && !e.basis_ref && <span className="chip bg-danger-soft text-danger">no death record</span>}
          </div>
          <p className="mt-0.5 text-sm text-slate-700">
            {e.from.length > 0 && <>{names(e.from)} → </>}
            <strong>{names(e.to)}</strong>
            {e.amount_inr ? <span className="text-slate-500"> · {inr(e.amount_inr)}</span> : null}
          </p>
          {e.basis_ref && (
            <p lang={lang} className="text-xs text-slate-400">
              {e.basis_ref}
            </p>
          )}
        </li>
      ))}
    </ol>
  )
}

export function ApiCall({ path, keyHint = false }: { path: string; keyHint?: boolean }) {
  const [copied, setCopied] = useState(false)
  const cmd = `curl -s "${API}${path}"${keyHint ? ' \\\n  -H "Authorization: Bearer $TITLIVO_KEY"' : ''}`
  return (
    <div className="rounded-xl bg-navy p-3 text-xs text-white" data-testid="api-call">
      <div className="mb-1 flex items-center justify-between text-white/60">
        <span>Show API call</span>
        <button
          className="rounded bg-white/10 px-2 py-0.5 hover:bg-white/20"
          onClick={() => {
            navigator.clipboard?.writeText(cmd)
            setCopied(true)
          }}
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto font-mono whitespace-pre-wrap">{cmd}</pre>
    </div>
  )
}
