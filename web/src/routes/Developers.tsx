import { API } from '../lib/api'

const block = (s: string) => (
  <pre className="overflow-x-auto rounded-xl bg-navy p-4 font-mono text-xs leading-relaxed text-white">{s.trim()}</pre>
)

export default function Developers() {
  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-8" data-testid="developers">
      <div>
        <h1 className="text-3xl font-bold text-navy">One API, three states</h1>
        <p className="mt-2 text-slate-600">
          The same JSON shape for a Maharashtra 7/12, a Karnataka RTC and a Gujarat 7/12 + 8-A. Every response carries the canonical record, the
          native record as the state issued it, and an <code>X-Coverage</code> header. Errors are RFC 9457 problem+json.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <a className="btn-primary" href={`${API}/docs`} target="_blank" rel="noreferrer">
            Interactive API reference ↗
          </a>
          <a className="btn-ghost" href="https://github.com/Gurjas2112/Titlivo/tree/main/postman" target="_blank" rel="noreferrer">
            Postman collection ↗
          </a>
        </div>
      </div>
      <section>
        <h2 className="mb-2 text-lg font-semibold">Quickstart</h2>
        {block(`
# search in any script (names are masked without a key)
curl -s "${API}/v1/parcels/search?q=214/2"

# full dossier: canonical + native record, title chain, flags, coverage
curl -s "${API}/v1/parcels/DEMO-27TEK337Z567G4" -H "Authorization: Bearer $TITLIVO_KEY"

# red flags only, each with evidence and the source record id
curl -s "${API}/v1/parcels/DEMO-27TEK337Z567G4/flags"

# issue a Title Passport, then verify it (no account needed to verify)
curl -s -X POST "${API}/v1/parcels/DEMO-27TEK337Z567G4/passports"
curl -s -X POST "${API}/v1/passports/verify" -H "Content-Type: application/json" -d '{"jwt":"<token>"}'
`)}
      </section>
      <section>
        <h2 className="mb-2 text-lg font-semibold">MCP for AI agents</h2>
        <p className="mb-2 text-sm text-slate-600">
          Tools: <code>search_parcels</code>, <code>get_parcel_dossier</code>, <code>get_title_chain</code>, <code>list_red_flags</code>. Same service
          layer as the REST API, same masking.
        </p>
        {block(`
npx @modelcontextprotocol/inspector
# Transport: Streamable HTTP · URL: ${API}/mcp/ · Header: Authorization: Bearer $TITLIVO_KEY

# Claude Code
claude mcp add --transport http titlivo ${API}/mcp/ --header "Authorization: Bearer $TITLIVO_KEY"
`)}
      </section>
      <section>
        <h2 className="mb-2 text-lg font-semibold">Verify passports yourself</h2>
        <p className="text-sm text-slate-600">
          Passports are W3C Verifiable Credentials 2.0 secured as <code>vc+jwt</code> with Ed25519. Fetch the issuer key from{' '}
          <a className="underline" href={`${API}/.well-known/did.json`}>
            /.well-known/did.json
          </a>{' '}
          and the live status from the signed Bitstring Status Lists{' '}
          <a className="underline" href={`${API}/status/1`}>
            /status/1
          </a>{' '}
          (suspension) and{' '}
          <a className="underline" href={`${API}/status/2`}>
            /status/2
          </a>{' '}
          (revocation). No Titlivo account or database access is needed.
        </p>
      </section>
    </div>
  )
}
