import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { StatusPill } from '../components/bits'
import { API, api, fmtDate } from '../lib/api'
import { verifyPassport, type VerifyResult } from '../lib/verifyPassport'

/** Public verifier: no login, mobile-first. Verifies in the browser, updates live over SSE. */
export default function Verifier() {
  const { passportId = '' } = useParams()
  const [jwt, setJwt] = useState<string | null>(null)
  const [r, setR] = useState<VerifyResult | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [, setNow] = useState(Date.now())

  useEffect(() => {
    api<{ jwt: string }>(`/v1/passports/${passportId}`)
      .then((p) => setJwt(p.jwt))
      .catch((e) => setErr(String(e)))
  }, [passportId])

  useEffect(() => {
    if (!jwt) return
    let alive = true
    const check = (bust: boolean) => verifyPassport(jwt, bust).then((x) => alive && setR(x))
    check(false)
    const es = new EventSource(`${API}/v/${passportId}/events`)
    es.addEventListener('status', () => check(true))
    const poll = setInterval(() => check(true), 60_000)
    const clock = setInterval(() => setNow(Date.now()), 1000)
    return () => {
      alive = false
      es.close()
      clearInterval(poll)
      clearInterval(clock)
    }
  }, [jwt, passportId])

  if (err) return <VerifierShell><p className="text-danger">Passport not found. {err}</p></VerifierShell>
  return <VerifierShell>{r ? <Result r={r} /> : <p className="text-center text-slate-500">Checking signature and live status…</p>}</VerifierShell>
}

export function VerifierShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-[480px] px-4 py-6" data-testid="verifier">
      <p className="text-center text-xs font-semibold tracking-widest text-slate-500 uppercase">Titlivo Title Passport · public verification</p>
      <div className="mt-3">{children}</div>
    </div>
  )
}

export function Result({ r }: { r: VerifyResult }) {
  const c = r.credential?.credentialSubject
  const ago = Math.max(0, Math.round((Date.now() - r.checkedAt.getTime()) / 1000))
  const tone =
    r.status === 'LIVE' ? 'from-mint/25' : r.status === 'SUSPENDED' ? 'from-saffron/25' : r.status === 'EXPIRED' ? 'from-slate-300/40' : 'from-danger/25'
  return (
    <div className="card overflow-hidden">
      <div className={`bg-gradient-to-b ${tone} to-white px-5 pt-8 pb-6 text-center`}>
        <StatusPill status={r.status} big />
        <p className="mt-4 text-sm font-medium" data-testid="signature-line">
          {r.status === 'INVALID_SIGNATURE' ? (
            <span className="text-danger">Signature does not verify. Do not rely on this document.</span>
          ) : (
            <>
              <span className="text-teal-700">✓ Signature valid</span> · issued by <span className="font-mono text-xs break-all">{r.issuer}</span>
            </>
          )}
        </p>
        {r.reasons.length > 0 && <p className="mt-2 text-sm text-saffron" data-testid="reasons">{r.reasons.join('; ')}</p>}
        <p className="mt-2 text-xs text-slate-400" data-testid="checked-ago">
          Status checked {ago}s ago · updates live
        </p>
      </div>
      {c && (
        <div className="space-y-4 px-5 pb-5 text-sm">
          <div className="rounded-xl bg-paper p-3">
            <div className="font-semibold">
              Survey {c.parcel.surveyNo}, {c.parcel.village}
            </div>
            <div className="text-xs text-slate-500">
              {c.parcel.district}, {c.parcel.state} · {c.parcel.recordType}
            </div>
            <div className="mt-1 font-mono text-xs text-slate-400">{c.parcel.ulpin}</div>
          </div>
          <div>
            <h3 className="mb-1 text-xs font-semibold text-slate-500 uppercase">Checks at issue</h3>
            <ul className="divide-y divide-slate-100">
              {c.checks.map((k) => (
                <li key={k.rule} className="flex items-center justify-between py-1.5">
                  <span>
                    <span className="mr-2 font-mono text-xs text-slate-400">{k.rule}</span>
                    {k.title.replace('Fraud Sentinel: ', '')}
                  </span>
                  <span className={`chip ${k.result === 'clear' ? 'bg-mint-soft text-teal-700' : 'bg-danger-soft text-danger'}`}>
                    {k.result === 'clear' ? '✓ clear' : '⚑ flag'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-xs">
            <dt className="text-slate-500">Owners</dt>
            <dd>{c.owners.count} (names not shared)</dd>
            <dt className="text-slate-500">Valid</dt>
            <dd>
              {fmtDate(r.credential!.validFrom.slice(0, 10))} → {fmtDate(r.credential!.validUntil.slice(0, 10))}
            </dd>
            <dt className="text-slate-500">Coverage</dt>
            <dd>
              {c.coverage.states.join(', ')} · as of {c.coverage.as_of}
            </dd>
          </dl>
          <p className="rounded-lg bg-saffron-soft p-3 text-[11px] text-slate-700" data-testid="disclaimer">
            {c.disclaimer}
          </p>
        </div>
      )}
    </div>
  )
}
