export const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://localhost:8000'
export const MAP_STYLE = (import.meta.env.VITE_MAP_STYLE as string | undefined) ?? 'https://tiles.openfreemap.org/styles/liberty'

export type Severity = 'high' | 'medium' | 'info'

export interface Person {
  id: string
  name: string
  name_local: string | null
  masked: boolean
}

export interface Flag {
  id: string
  title: string
  severity: Severity
  material: boolean
  text: string
  basis: string
  evidence: Record<string, unknown>
  source_record_id: string
}

export interface ChainEvent {
  position: number
  event_type: string
  native_term: string
  native_term_en: string | null
  registered_on: string
  from: Person[]
  to: Person[]
  consistent: boolean
  doc_no: string | null
  amount_inr: number | null
  mutation_no: string
  mutation_status: string
  basis_ref: string | null
  injected: boolean
  source_record_id: string
}

export interface Encumbrance {
  id: string
  kind: string
  native_term: string
  lender: string
  amount_inr: number
  created_on: string
  released_on: string | null
  status: string
  mutation_no: string
  injected: boolean
}

export interface Dossier {
  id: string
  version: number
  canonical: {
    state: string
    state_code: string
    state_record: string
    district: string
    taluk: string
    village: string
    village_local: string
    survey_no: string
    area_m2: number
    mapped_area_m2: number
    area_native: { value: string; unit: string }
    tenure_class: string
    tenure_en: string
    tenure_restricted: boolean
    land_class: string
    holders: (Person & { share: number })[]
    centroid: { lat: number; lon: number }
  }
  native: { record_type: string; system: string; as_of: string; record: Record<string, unknown> }
  geometry: GeoJSON.Polygon
  title_chain: ChainEvent[]
  encumbrances: Encumbrance[]
  litigation: { id: string; case_no: string; court: string; status: string; filed_on: string }[]
  flags: Flag[]
  summary: string
  coverage: { states: string[]; sources: string[]; as_of: string; synthetic: boolean }
  names_masked: boolean
  source_record_id: string
  disclaimer: string
  passports: { id: string; issued_at: string; valid_until: string; verify_url: string }[]
}

export interface SearchHit {
  id: string
  survey_no: string
  state: string
  village: string
  village_local: string
  district: string
  flag_count: number
  max_severity: Severity | null
}

export interface IssuedPassport {
  id: string
  jwt: string
  verify_url: string
  qr_svg: string
}

export const STATE_LANG: Record<string, string> = { '27': 'mr', '29': 'kn', '24': 'gu' }

function authHeaders(): Record<string, string> {
  let key: string | null = null
  try {
    key = sessionStorage.getItem('titlivo.key')
  } catch {
    /* storage unavailable */
  }
  return key ? { Authorization: `Bearer ${key}` } : {}
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(init.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const p = await res.json()
      detail = p.detail ?? p.title ?? detail
    } catch {
      /* not json */
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export const inr = (n: number) => '₹' + n.toLocaleString('en-IN')
export const sqm = (n: number) => `${Math.round(n).toLocaleString('en-IN')} m²`
export const ha = (n: number) => `${(n / 10000).toFixed(2)} ha`
export const fmtDate = (s: string) =>
  new Date(s + (s.length === 10 ? 'T00:00:00' : '')).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
