import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { api, type Flag } from '../lib/api'

interface InjectResult {
  preset?: string
  new_material_flags?: string[]
  suspended_passports?: string[]
  reinstated_passports?: string[]
  flags: Flag[]
}

const read = (k: string) => {
  try {
    return sessionStorage.getItem(k) ?? ''
  } catch {
    return ''
  }
}

/** Admin panel for the live-revocation demo: inject a registry event, watch passports suspend. */
export default function Admin() {
  const [key, setKey] = useState(read('titlivo.key'))
  const [parcel, setParcel] = useState('')
  const [presets, setPresets] = useState<Record<string, string>>({})
  const [log, setLog] = useState<{ at: string; text: string; ok: boolean }[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api<Record<string, string>>('/v1/admin/presets').then(setPresets)
    api<Record<string, string>>('/v1/demo/parcels').then((d) => setParcel((p) => p || d.hero))
  }, [])

  const saveKey = (v: string) => {
    setKey(v)
    try {
      sessionStorage.setItem('titlivo.key', v)
    } catch {
      /* storage unavailable */
    }
  }

  const call = async (path: string, body: object, label: string) => {
    setBusy(true)
    try {
      const r = await api<InjectResult>(path, { method: 'POST', body: JSON.stringify(body), headers: { Authorization: `Bearer ${key}` } })
      const text =
        r.suspended_passports !== undefined
          ? `${label}: new material flags ${r.new_material_flags?.join(', ') || 'none'} · ${r.suspended_passports.length} passport(s) suspended`
          : `${label}: ${r.reinstated_passports?.length ?? 0} passport(s) reinstated`
      setLog((l) => [{ at: new Date().toLocaleTimeString(), text, ok: true }, ...l])
    } catch (e) {
      setLog((l) => [{ at: new Date().toLocaleTimeString(), text: `${label}: ${e}`, ok: false }, ...l])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8" data-testid="admin">
      <h1 className="text-2xl font-bold text-navy">Inject a registry event</h1>
      <p className="mt-1 text-sm text-slate-600">
        Simulates a new entry arriving from the registration or revenue system. In one database transaction Titlivo re-runs every rule, and if a
        new material flag appears it flips the suspension bit of every live passport for the parcel. Open verifiers update within seconds.
      </p>
      <div className="card mt-6 space-y-4 p-5">
        <label className="block text-sm">
          <span className="font-medium">Admin API key</span>
          <input
            type="password"
            value={key}
            onChange={(e) => saveKey(e.target.value)}
            placeholder="tlv_admin_…"
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-sm"
            data-testid="admin-key"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Parcel</span>
          <input
            value={parcel}
            onChange={(e) => setParcel(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 font-mono text-sm"
            data-testid="admin-parcel"
          />
          {parcel && (
            <Link to={`/p/${parcel}`} target="_blank" className="mt-1 inline-block text-xs text-navy underline">
              Open this parcel ↗
            </Link>
          )}
        </label>
        <div className="grid gap-2 sm:grid-cols-2">
          {Object.entries(presets).map(([id, label]) => (
            <button
              key={id}
              disabled={busy || !key}
              onClick={() => call('/v1/admin/events', { parcel_id: parcel, preset: id }, label)}
              className="btn-ghost justify-start text-left"
              data-testid={`preset-${id}`}
            >
              ⚡ {label}
            </button>
          ))}
        </div>
        <button className="btn-ghost w-full" disabled={busy || !key} onClick={() => call('/v1/admin/demo/reset', { parcel_id: parcel }, 'Reset demo')} data-testid="reset">
          ↺ Reset demo (remove injected events, reinstate passports)
        </button>
      </div>
      <ul className="mt-6 space-y-2 text-sm" data-testid="admin-log">
        {log.map((l, i) => (
          <li key={i} className={`rounded-lg p-3 ${l.ok ? 'bg-mint-soft' : 'bg-danger-soft text-danger'}`}>
            <span className="mr-2 font-mono text-xs text-slate-500">{l.at}</span>
            {l.text}
          </li>
        ))}
      </ul>
    </div>
  )
}
