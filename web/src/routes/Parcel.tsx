import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import AskBox from '../components/AskBox'
import MapView from '../components/MapView'
import PassportCard from '../components/PassportCard'
import { ApiCall, FlagCard, Timeline } from '../components/bits'
import { API, STATE_LANG, api, fmtDate, ha, inr, sqm, type Dossier } from '../lib/api'

const UNIT_LABEL: Record<string, string> = { hectare_are: 'hectare.are', acre_gunta: 'acre-gunta', hectare_are_sqm: 'hectare-are-sq m' }

export default function Parcel() {
  const { parcelId = '' } = useParams()
  const [d, setD] = useState<Dossier | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [tab, setTab] = useState<'canonical' | 'native'>('canonical')
  const [tick, setTick] = useState(0)

  const load = useCallback(() => {
    api<Dossier>(`/v1/parcels/${parcelId}`)
      .then((x) => {
        setD(x)
        setErr(null)
      })
      .catch((e) => setErr(String(e)))
  }, [parcelId])

  useEffect(() => {
    load()
    const es = new EventSource(`${API}/v1/parcels/${parcelId}/events`)
    es.addEventListener('changed', () => {
      load()
      setTick((t) => t + 1)
    })
    return () => es.close()
  }, [parcelId, load])

  if (err) return <p className="mx-auto max-w-7xl p-8 text-danger">{err}</p>
  if (!d) return <p className="mx-auto max-w-7xl p-8 text-slate-500">Loading parcel…</p>
  const c = d.canonical
  const lang = STATE_LANG[c.state_code]
  const high = d.flags.filter((f) => f.severity === 'high').length

  return (
    <div className="mx-auto max-w-7xl px-4 py-6" data-testid="dossier">
      <Link to="/" className="text-sm text-slate-500 hover:text-navy">
        ← Search
      </Link>
      <div className="mt-2 grid gap-6 lg:grid-cols-[1.05fr_1fr]">
        {/* left: map + timeline */}
        <div className="space-y-6">
          <div className="h-[380px]">
            <MapView highlightId={d.id} focus={d.geometry} refreshKey={tick} />
          </div>
          <div className="card p-5">
            <h3 className="font-semibold text-navy">Chain of title</h3>
            <p className="mb-4 text-xs text-slate-500">
              Computed in SQL from the mutation register: each transfer is checked against the holders recorded at that time.
            </p>
            <Timeline events={d.title_chain} lang={lang} />
          </div>
          <div className="card p-5">
            <h3 className="font-semibold text-navy">Mortgages and court cases</h3>
            {d.encumbrances.length === 0 && d.litigation.length === 0 && <p className="mt-2 text-sm text-slate-500">None recorded.</p>}
            <ul className="mt-2 space-y-2 text-sm">
              {d.encumbrances.map((e) => (
                <li key={e.id} className="flex flex-wrap items-center gap-2">
                  <span className={`chip ${e.status === 'active' ? 'bg-danger-soft text-danger' : 'bg-mint-soft text-teal-700'}`}>{e.status}</span>
                  <span>
                    {inr(e.amount_inr)} mortgage to <span lang={lang}>{e.lender}</span>, {fmtDate(e.created_on)}
                    {e.released_on ? ` → released ${fmtDate(e.released_on)}` : ''}
                  </span>
                  <span className="font-mono text-xs text-slate-400">entry {e.mutation_no}</span>
                </li>
              ))}
              {d.litigation.map((l) => (
                <li key={l.id} className="flex flex-wrap items-center gap-2">
                  <span className="chip bg-danger-soft text-danger">{l.status}</span>
                  Case {l.case_no} · <span lang={lang}>{l.court}</span> · filed {fmtDate(l.filed_on)}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* right: identity, flags, passport, ask, API */}
        <div className="space-y-6">
          <div className="card p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  {c.state} · {c.state_record}
                </p>
                <h1 className="text-2xl font-bold text-navy" data-testid="parcel-title">
                  Survey {c.survey_no}, {c.village}
                </h1>
                <p className="text-sm text-slate-500">
                  <span lang={lang}>{c.village_local}</span> · {c.taluk}, {c.district}
                </p>
              </div>
              <span className="chip bg-saffron-soft font-mono text-saffron">{d.id}</span>
            </div>
            <div
              className={`mt-4 rounded-xl p-3 text-sm font-medium ${d.flags.length ? (high ? 'bg-danger-soft text-danger' : 'bg-saffron-soft text-saffron') : 'bg-mint-soft text-teal-800'}`}
              data-testid="summary"
            >
              {d.summary}
            </div>
            <div className="mt-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-xs font-semibold">
              {(['canonical', 'native'] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)} className={`flex-1 rounded-md py-1.5 ${tab === t ? 'bg-white shadow' : 'text-slate-500'}`}>
                  {t === 'canonical' ? 'Canonical (one schema)' : `Native record (${d.native.system})`}
                </button>
              ))}
            </div>
            {tab === 'canonical' ? (
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm" data-testid="canonical">
                <dt className="text-slate-500">Recorded area</dt>
                <dd>
                  {sqm(c.area_m2)} <span className="text-slate-400">({ha(c.area_m2)})</span>
                </dd>
                <dt className="text-slate-500">As written</dt>
                <dd lang={lang}>
                  {c.area_native.value} <span className="text-slate-400">{UNIT_LABEL[c.area_native.unit]}</span>
                </dd>
                <dt className="text-slate-500">Mapped area</dt>
                <dd>{sqm(c.mapped_area_m2)}</dd>
                <dt className="text-slate-500">Tenure</dt>
                <dd>
                  {c.tenure_en}
                  {c.tenure_restricted && <span className="chip ml-1 bg-danger-soft text-danger">restricted</span>}
                </dd>
                <dt className="text-slate-500">Recorded holders</dt>
                <dd>
                  {c.holders.map((h) => (
                    <div key={h.id}>
                      {h.name} {h.name_local && <span lang={lang} className="text-slate-400">({h.name_local})</span>}
                    </div>
                  ))}
                  {d.names_masked && <div className="text-[11px] text-slate-400">masked for anonymous users</div>}
                </dd>
              </dl>
            ) : (
              <pre lang={lang} className="mt-3 max-h-72 overflow-auto rounded-lg bg-paper p-3 text-xs" data-testid="native">
                {JSON.stringify(d.native.record, null, 1)}
              </pre>
            )}
          </div>

          <div className="space-y-3" data-testid="flags">
            <h3 className="font-semibold text-navy">Red flags {d.flags.length > 0 && <span className="text-slate-400">({d.flags.length})</span>}</h3>
            {d.flags.length === 0 && (
              <p className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                No red flags found in the records available to Titlivo. Coverage: {d.coverage.sources.join(', ')}; as of {d.coverage.as_of}.
              </p>
            )}
            {d.flags.map((f) => (
              <FlagCard key={f.id + JSON.stringify(f.evidence)} f={f} />
            ))}
          </div>

          <PassportCard parcelId={d.id} existing={d.passports} />
          <AskBox parcelId={d.id} defaultLang={lang} />
          <ApiCall path={`/v1/parcels/${d.id}`} keyHint />
          <p className="text-[11px] text-slate-400">{d.disclaimer}</p>
        </div>
      </div>
    </div>
  )
}
