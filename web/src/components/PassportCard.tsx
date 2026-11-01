import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, fmtDate, type IssuedPassport } from '../lib/api'
import { verifyPassport, type VerifyResult } from '../lib/verifyPassport'
import { StatusPill } from './bits'

export default function PassportCard({ parcelId, existing }: { parcelId: string; existing: { id: string }[] }) {
  const [passport, setPassport] = useState<IssuedPassport | null>(null)
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (passport || existing.length === 0) return
    api<IssuedPassport>(`/v1/passports/${existing[0].id}`).then(setPassport).catch(() => {})
  }, [existing, passport])

  useEffect(() => {
    if (!passport) return
    let alive = true
    const check = (bust: boolean) => verifyPassport(passport.jwt, bust).then((r) => alive && setResult(r))
    check(false)
    const es = new EventSource(`${(import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')}/v/${passport.id}/events`)
    es.addEventListener('status', () => check(true))
    return () => {
      alive = false
      es.close()
    }
  }, [passport])

  const issue = async () => {
    setBusy(true)
    setErr(null)
    try {
      setPassport(await api<IssuedPassport>(`/v1/parcels/${parcelId}/passports`, { method: 'POST' }))
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(false)
    }
  }

  const download = () => {
    if (!passport) return
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([passport.jwt], { type: 'application/vc+jwt' }))
    a.download = `titlivo-passport-${passport.id.slice(0, 8)}.jwt`
    a.click()
  }

  return (
    <div className="card overflow-hidden" data-testid="passport-card">
      <div className="flex items-center justify-between bg-navy px-5 py-3 text-white">
        <div>
          <div className="text-xs tracking-widest text-white/60 uppercase">Titlivo</div>
          <div className="font-semibold">Title Passport</div>
        </div>
        {result && <StatusPill status={result.status} />}
      </div>
      {!passport ? (
        <div className="p-5">
          <p className="text-sm text-slate-600">
            Turn this check into a signed W3C Verifiable Credential. Anyone can verify it by QR, link or API, without an account. It flips to
            SUSPENDED automatically if the records change.
          </p>
          <button className="btn-primary mt-4 w-full" onClick={issue} disabled={busy} data-testid="issue-passport">
            {busy ? 'Signing…' : 'Issue Title Passport'}
          </button>
          {err && <p className="mt-2 text-xs text-danger">{err}</p>}
        </div>
      ) : (
        <div className="grid gap-4 p-5 sm:grid-cols-[150px_1fr]">
          <div className="rounded-xl bg-white p-1 ring-1 ring-slate-200 [&_svg]:h-auto [&_svg]:w-full" dangerouslySetInnerHTML={{ __html: passport.qr_svg }} />
          <div className="space-y-2 text-sm">
            {result?.credential && (
              <>
                <p>
                  <span className="text-slate-500">Checks:</span>{' '}
                  {result.credential.credentialSubject.checks.filter((c) => c.result === 'clear').length} clear,{' '}
                  {result.credential.credentialSubject.summary.flags} flagged
                </p>
                <p>
                  <span className="text-slate-500">Owners:</span> {result.credential.credentialSubject.owners.count} (names not included)
                </p>
                <p>
                  <span className="text-slate-500">Valid until:</span> {fmtDate(result.credential.validUntil.slice(0, 10))}
                </p>
              </>
            )}
            {result && result.status !== 'LIVE' && <p className="text-xs font-medium text-saffron">{result.reasons.join('; ')}</p>}
            <div className="flex flex-wrap gap-2 pt-1">
              <Link to={`/v/${passport.id}`} target="_blank" className="btn-ghost py-1.5 text-xs" data-testid="open-verifier">
                Open public verifier ↗
              </Link>
              <button className="btn-ghost py-1.5 text-xs" onClick={download}>
                Download .jwt
              </button>
            </div>
            <p className="font-mono text-[10px] break-all text-slate-400">{passport.id}</p>
          </div>
        </div>
      )}
      <p className="border-t border-slate-100 px-5 py-2 text-[11px] text-slate-500">
        Attests only to the records available to Titlivo. Not a guarantee, certificate of title or legal opinion.
      </p>
    </div>
  )
}
