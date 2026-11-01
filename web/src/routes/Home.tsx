import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import MapView from '../components/MapView'
import { SeverityChip } from '../components/bits'
import { api, type SearchHit } from '../lib/api'

const EXAMPLES = ['214/2', 'नितीन भोसले', 'Nitin Bhosale', 'Nandikere', 'પટેલ']
const FLAG_LABELS: Record<string, string> = {
  F01: 'Chain break',
  F02: 'Unreleased mortgage',
  F03: 'Pending litigation',
  F04: 'Area mismatch',
  F05: 'Restricted tenure',
  F06: 'Rapid resale',
  F11: 'Double sale',
  F12: 'Fake heirs',
  F16: 'Sold while mortgaged',
}

export default function Home() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const [hits, setHits] = useState<SearchHit[] | null>(null)
  const [demo, setDemo] = useState<Record<string, string>>({})
  const [err, setErr] = useState<string | null>(null)
  const nav = useNavigate()
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api<Record<string, string>>('/v1/demo/parcels').then(setDemo).catch(() => {})
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        input.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    const term = params.get('q')
    if (!term) return
    setErr(null)
    api<{ results: SearchHit[] }>(`/v1/parcels/search?q=${encodeURIComponent(term)}`)
      .then((r) => setHits(r.results))
      .catch((e) => setErr(String(e)))
  }, [params])

  const run = (term: string) => {
    setQ(term)
    setParams({ q: term })
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <section className="grid gap-8 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <p className="text-sm font-semibold tracking-wide text-saffron uppercase">Land titles that stay alive</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-navy md:text-5xl">
            One parcel API across three states. One check, verifiable by anyone.
          </h1>
          <p className="mt-4 text-lg text-slate-600">
            Search Maharashtra 7/12, Karnataka RTC and Gujarat 7/12 records in any script. Titlivo harmonises them, computes the title chain and red
            flags in SQL, and issues a signed <strong>Title Passport</strong> that flips to SUSPENDED when the records change.
          </p>
          <form
            className="mt-6 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (q.trim()) run(q.trim())
            }}
          >
            <input
              ref={input}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Survey no, owner name (any script) or village   ( / )"
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base shadow-sm outline-none focus:border-navy focus:ring-2 focus:ring-navy/20"
              aria-label="Search parcels"
              data-testid="search-input"
            />
            <button className="btn-primary px-6" data-testid="search-button">
              Search
            </button>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-slate-500">Try:</span>
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => run(ex)} className="chip bg-white text-navy ring-1 ring-slate-200 hover:ring-navy">
                {ex}
              </button>
            ))}
          </div>

          {err && <p className="mt-4 text-sm text-danger">{err}</p>}
          {hits && (
            <div className="card mt-6 divide-y divide-slate-100" data-testid="results">
              {hits.length === 0 && <p className="p-4 text-sm text-slate-500">No parcels match “{params.get('q')}”.</p>}
              {hits.map((h) => (
                <Link key={h.id} to={`/p/${h.id}`} className="flex items-center justify-between gap-3 p-4 hover:bg-slate-50" data-testid="result">
                  <div>
                    <div className="font-semibold">
                      Survey {h.survey_no} · {h.village} <span className="text-slate-400">({h.state})</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {h.village_local} · {h.district} · <span className="font-mono">{h.id}</span>
                    </div>
                  </div>
                  {h.max_severity ? (
                    <span className="flex items-center gap-2 text-xs">
                      {h.flag_count} flag{h.flag_count > 1 ? 's' : ''} <SeverityChip s={h.max_severity} />
                    </span>
                  ) : (
                    <span className="chip bg-mint-soft text-teal-700">No red flags found</span>
                  )}
                </Link>
              ))}
            </div>
          )}

          {Object.keys(demo).length > 0 && (
            <div className="mt-8">
              <h2 className="text-sm font-semibold text-slate-500 uppercase">Tour: one parcel, three audiences</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {demo.hero && (
                  <Link to={`/p/${demo.hero}`} className="btn-primary" data-testid="tour">
                    Start with survey 214/2, Sahyagaon →
                  </Link>
                )}
              </div>
              <h2 className="mt-6 text-sm font-semibold text-slate-500 uppercase">See each red flag on a real-looking record</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(FLAG_LABELS).map(([id, label]) =>
                  demo[id] ? (
                    <Link key={id} to={`/p/${demo[id]}`} className="chip bg-white py-1 text-slate-700 ring-1 ring-slate-200 hover:ring-danger">
                      <span className="font-mono text-slate-400">{id}</span> {label}
                    </Link>
                  ) : null,
                )}
              </div>
            </div>
          )}
        </div>
        <div className="h-[560px]">
          <MapView onSelect={(id) => nav(`/p/${id}`)} />
          <div className="mt-2 flex gap-4 text-xs text-slate-500">
            <span>
              <i className="mr-1 inline-block h-3 w-3 rounded bg-mint align-middle" />
              no red flags found
            </span>
            <span>
              <i className="mr-1 inline-block h-3 w-3 rounded bg-amber align-middle" />
              medium
            </span>
            <span>
              <i className="mr-1 inline-block h-3 w-3 rounded bg-danger align-middle" />
              high severity
            </span>
          </div>
        </div>
      </section>
    </div>
  )
}
