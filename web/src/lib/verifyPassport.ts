/**
 * Browser-side Title Passport verifier (spec §6.10). Same algorithm as
 * api/src/titlivo/services/passport_verify.py: it trusts only the issuer's published
 * did.json and the signed status lists, never the Titlivo database.
 */
import { compactVerify, decodeProtectedHeader, importJWK } from 'jose'

export type PassportStatus = 'LIVE' | 'SUSPENDED' | 'REVOKED' | 'EXPIRED' | 'INVALID_SIGNATURE' | 'UNVERIFIED'

export interface Credential {
  issuer: string
  validFrom: string
  validUntil: string
  credentialSubject: {
    parcel: { ulpin: string; state: string; district: string; village: string; surveyNo: string; recordedAreaM2: number; recordType: string }
    owners: { count: number; commitment: string }
    checks: { rule: string; title: string; result: 'flag' | 'clear'; severity: string; evidenceDigest?: string }[]
    summary: { flags: number; high: number }
    coverage: { states: string[]; sources: string[]; as_of: string; synthetic: boolean }
    disclaimer: string
  }
  credentialStatus: { statusPurpose: 'suspension' | 'revocation'; statusListIndex: string; statusListCredential: string }[]
}

export interface VerifyResult {
  status: PassportStatus
  reasons: string[]
  issuer?: string
  credential?: Credential
  checkedAt: Date
}

const ALG = 'Ed25519'
const td = new TextDecoder()

export function didWebUrl(did: string): string {
  if (!did.startsWith('did:web:')) throw new Error('only did:web issuers are supported')
  const parts = did.slice(8).split(':').map(decodeURIComponent)
  const host = parts[0]
  const scheme = host.startsWith('localhost') || host.startsWith('127.0.0.1') ? 'http' : 'https'
  return parts.length > 1 ? `${scheme}://${host}/${parts.slice(1).join('/')}/did.json` : `${scheme}://${host}/.well-known/did.json`
}

async function verifyJws(token: string, bust: boolean): Promise<Record<string, any>> {
  const header = decodeProtectedHeader(token)
  if (header.typ !== 'vc+jwt' || header.alg !== ALG || !header.kid) throw new Error('unexpected header')
  const issuer = header.kid.split('#')[0]
  const doc = await (await fetch(didWebUrl(issuer), { cache: bust ? 'no-store' : 'default' })).json()
  const vm = (doc.verificationMethod ?? []).find((m: { id: string }) => m.id === header.kid)
  if (!vm) throw new Error('signing key not found in did.json')
  const key = await importJWK(vm.publicKeyJwk, ALG)
  const { payload } = await compactVerify(token, key, { algorithms: [ALG] })
  const cred = JSON.parse(td.decode(payload))
  if (cred.issuer !== issuer) throw new Error('issuer does not match signing key')
  return cred
}

async function decodeList(encoded: string): Promise<Uint8Array> {
  if (!encoded.startsWith('u')) throw new Error('encodedList must be multibase base64url')
  const b64 = encoded.slice(1).replace(/-/g, '+').replace(/_/g, '/')
  const bin = Uint8Array.from(atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4)), (c) => c.charCodeAt(0))
  const stream = new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))
  return new Uint8Array(await new Response(stream).arrayBuffer())
}

const bitAt = (bits: Uint8Array, i: number) => (bits[i >> 3] & (0x80 >> (i & 7))) !== 0

/** bust = true skips HTTP caches (used when the server pushes a status change). */
export async function verifyPassport(jwt: string, bust = false, now = new Date()): Promise<VerifyResult> {
  let cred: Credential
  try {
    cred = (await verifyJws(jwt.trim(), false)) as Credential
  } catch (e) {
    return { status: 'INVALID_SIGNATURE', reasons: [`signature or issuer check failed: ${(e as Error).message}`], checkedAt: now }
  }
  const result: VerifyResult = { status: 'LIVE', reasons: [], issuer: cred.issuer, credential: cred, checkedAt: now }
  if (new Date(cred.validUntil) < now) {
    result.status = 'EXPIRED'
    result.reasons.push(`expired on ${cred.validUntil}`)
  }
  for (const entry of cred.credentialStatus ?? []) {
    try {
      const url = entry.statusListCredential + (bust ? `?t=${Date.now()}` : '')
      const res = await fetch(url, { cache: bust ? 'no-store' : 'default' })
      const sl = await verifyJws(await res.text(), false)
      if (sl.credentialSubject.statusPurpose !== entry.statusPurpose) throw new Error('status purpose mismatch')
      const bits = await decodeList(sl.credentialSubject.encodedList)
      if (bitAt(bits, Number(entry.statusListIndex))) {
        if (entry.statusPurpose === 'revocation') {
          result.status = 'REVOKED'
          result.reasons.push('revoked by the issuer')
        } else if (result.status === 'LIVE') {
          result.status = 'SUSPENDED'
          result.reasons.push('suspended: a material change was detected in the records')
        }
      }
    } catch (e) {
      if (result.status === 'LIVE') result.status = 'UNVERIFIED'
      result.reasons.push(`status list check failed: ${(e as Error).message}`)
    }
  }
  return result
}
