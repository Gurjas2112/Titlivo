import { useState } from 'react'
import { verifyPassport, type VerifyResult } from '../lib/verifyPassport'
import { Result, VerifierShell } from './Verifier'

/** Verify any passport file (.jwt) or pasted token, entirely in the browser. */
export default function Verify() {
  const [text, setText] = useState('')
  const [r, setR] = useState<VerifyResult | null>(null)
  const [busy, setBusy] = useState(false)

  const run = async (token: string) => {
    setBusy(true)
    setR(await verifyPassport(token, true))
    setBusy(false)
  }

  return (
    <VerifierShell>
      <div
        className="card p-5"
        onDragOver={(e) => e.preventDefault()}
        onDrop={async (e) => {
          e.preventDefault()
          const f = e.dataTransfer.files[0]
          if (f) {
            const t = await f.text()
            setText(t)
            run(t)
          }
        }}
      >
        <h1 className="text-lg font-semibold text-navy">Verify a Title Passport</h1>
        <p className="text-sm text-slate-500">
          Drop a <code>.jwt</code> file or paste the token. The signature and live status are checked in your browser against the issuer's published
          keys and status lists.
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          className="mt-3 w-full rounded-xl border border-slate-300 p-3 font-mono text-xs"
          placeholder="eyJhbGciOiJFZDI1NTE5Ii…"
          data-testid="jwt-input"
        />
        <button className="btn-primary mt-2 w-full" disabled={busy || text.trim().length < 20} onClick={() => run(text)} data-testid="verify-button">
          {busy ? 'Verifying…' : 'Verify'}
        </button>
      </div>
      {r && (
        <div className="mt-4">
          <Result r={r} />
        </div>
      )}
    </VerifierShell>
  )
}
