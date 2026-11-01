// Flow-wise screenshots → demo-media/screenshots/<NN-flow>/<NN-step>[-mobile].png + manifest.json
// Run: npm run demo:shots   (API + web running, data loaded with seed 42)
import { chromium } from '@playwright/test'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { API, OUT, WEB, demoParcels, envKey, post, run, terminalHtml } from './common.mjs'

const SHOTS = resolve(OUT, 'screenshots')
const manifest = []
const ADMIN = envKey('ADMIN_API_KEY')
const FLAG_ORDER = ['F01', 'F02', 'F03', 'F04', 'F05', 'F06', 'F11', 'F12', 'F16']

rmSync(SHOTS, { recursive: true, force: true })
const browser = await chromium.launch()
const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true })
const demo = await demoParcels()

async function shot(page, flow, step, title, caption, opts = {}) {
  const dir = resolve(SHOTS, flow)
  mkdirSync(dir, { recursive: true })
  const file = `${step}${opts.suffix ?? ''}.png`
  if (opts.locator) await opts.locator.screenshot({ path: resolve(dir, file) })
  else await page.screenshot({ path: resolve(dir, file), fullPage: !!opts.fullPage })
  manifest.push({ flow, step, file: `screenshots/${flow}/${file}`, title, caption, viewport: opts.suffix === '-mobile' ? 'mobile' : 'desktop' })
  console.log('  ✓', flow, file)
}

// Pages keep a live SSE connection open, so "network idle" never happens: wait for load + a fixed delay.
async function settle(page, ms = 2500) {
  await page.waitForLoadState('load').catch(() => {})
  await page.waitForTimeout(ms)
}

const d = await desktop.newPage()
const m = await mobile.newPage()
for (const pg of [d, m]) pg.setDefaultTimeout(20_000)
await post('/v1/admin/demo/reset', { parcel_id: demo.hero }, ADMIN)

// 01 Home and search
await d.goto(WEB)
await settle(d, 3500)
await shot(d, '01-home-and-search', '01-home', 'Home', 'One search box for any script; the map shows the six demo villages across three states.')
await d.getByTestId('search-input').fill('214/2')
await d.getByTestId('search-button').click()
await settle(d, 1500)
await shot(d, '01-home-and-search', '02-search-survey', 'Search by survey number', 'Survey 214/2 found in Maharashtra and Gujarat with the same canonical shape.')
await d.goto(`${WEB}/?q=${encodeURIComponent('नितीन भोसले')}`)
await settle(d, 1500)
await shot(d, '01-home-and-search', '03-search-devanagari', 'Search an owner name in Devanagari', 'Cross-script search: the Marathi name finds the same parcel as "Nitin Bhosale".')
await m.goto(WEB)
await settle(m, 3000)
await shot(m, '01-home-and-search', '04-home', 'Home on a phone', 'The same app on a 390 px phone screen.', { suffix: '-mobile' })

// 02 Dossier: canonical vs native, title chain
await d.goto(`${WEB}/p/${demo.hero}`)
await settle(d, 4000)
await shot(d, '02-dossier', '01-dossier', 'Parcel dossier', 'Survey 214/2: map, identity, "No red flags found in the records available to Titlivo" with coverage.')
await shot(d, '02-dossier', '02-dossier-full', 'Full dossier', 'Chain of title, mortgages, passport, Ask and the API call on one page.', { fullPage: true })
await d.getByRole('button', { name: /Native record/ }).click()
await d.waitForTimeout(500)
await shot(d, '02-dossier', '03-native-record', 'The native 7/12 record', 'The record exactly as Maharashtra writes it: Marathi keys, Devanagari numerals, hectare-are units.', {
  locator: d.getByTestId('native').locator('..'),
})
await shot(d, '02-dossier', '04-title-chain', 'Chain of title', 'Computed in SQL: every transfer checked against the holders recorded at the time.', {
  locator: d.getByTestId('timeline').locator('..'),
})

// 03 One screenshot per red flag
for (const [i, id] of FLAG_ORDER.entries()) {
  if (!demo[id]) continue
  await d.goto(`${WEB}/p/${demo[id]}`)
  await settle(d, 2500)
  const card = d.getByTestId(`flag-${id}`).first()
  await card.scrollIntoViewIfNeeded()
  await shot(d, '03-red-flags', `${String(i + 1).padStart(2, '0')}-${id}`, `Red flag ${id}`, 'Plain-language text built only from the SQL evidence, with the source record id.', {
    locator: d.getByTestId('flags'),
  })
}
await d.goto(`${WEB}/p/${demo.F12}`)
await settle(d, 3000)
await shot(d, '03-red-flags', '10-F12-timeline', 'Fake heirs on the timeline', 'Heirs added with no death record, then a sale weeks later: the Keesara pattern.', {
  locator: d.getByTestId('timeline').locator('..'),
})

// 04 Ask the property
await d.goto(`${WEB}/p/${demo.F02}`)
await settle(d, 2500)
await d.getByRole('button', { name: 'Is there a loan on this land?' }).click()
await d.getByTestId('answer').waitFor()
await d.waitForTimeout(600)
await shot(d, '04-ask', '01-loan-answer', 'Ask the property', 'Answer grounded in the records, with citations; never says "safe".', { locator: d.getByTestId('ask') })

// 05 Issue a Title Passport
await d.goto(`${WEB}/p/${demo.hero}`)
await settle(d, 3000)
await d.getByTestId('passport-card').scrollIntoViewIfNeeded()
if (await d.getByTestId('issue-passport').isVisible()) await d.getByTestId('issue-passport').click()
await d.getByTestId('passport-card').getByTestId('status-pill').waitFor()
await d.waitForTimeout(1200)
await shot(d, '05-title-passport', '01-passport-card', 'Title Passport issued', 'A signed W3C Verifiable Credential with QR; no owner names inside.', { locator: d.getByTestId('passport-card') })
const passportId = (await (await fetch(`${API}/v1/parcels/${demo.hero}`)).json()).passports[0].id

// 06 Public verifier, LIVE
await d.goto(`${WEB}/v/${passportId}`)
await d.getByTestId('status-pill').waitFor()
await settle(d, 1200)
await shot(d, '06-verifier', '01-live-desktop', 'Public verifier: LIVE', 'Anyone can verify: signature and live status checked in the browser, no login.')
await m.goto(`${WEB}/v/${passportId}`)
await m.getByTestId('status-pill').waitFor()
await settle(m, 1200)
await shot(m, '06-verifier', '02-live', 'Verifier on a phone: LIVE', 'What a bank officer sees after scanning the QR.', { suffix: '-mobile', fullPage: true })

// 07 Live revocation: inject F12 → SUSPENDED
await d.goto(`${WEB}/admin`)
await d.getByTestId('admin-key').fill(ADMIN)
await d.getByTestId('admin-parcel').fill(demo.hero)
await shot(d, '07-live-revocation', '01-admin-panel', 'Admin: inject a registry event', 'Simulates a new entry from the registration or revenue system.')
await d.getByTestId('preset-heir_impersonation').click()
await d.getByTestId('admin-log').locator('li').first().waitFor()
await d.waitForTimeout(800)
await shot(d, '07-live-revocation', '02-injected', 'Event injected', 'Fraud Sentinel raised F12; the passport was suspended in the same transaction.')
await m.reload()
await m.locator('[data-status="SUSPENDED"]').waitFor({ timeout: 10000 })
await m.waitForTimeout(800)
await shot(m, '07-live-revocation', '03-suspended', 'Verifier: SUSPENDED', 'The same QR now shows SUSPENDED with the reason.', { suffix: '-mobile' })
await d.goto(`${WEB}/p/${demo.hero}`)
await settle(d, 3000)
await shot(d, '07-live-revocation', '04-dossier-after', 'Dossier after the event', 'The new heir entries and the F12 flag appear on the parcel.', { fullPage: true })
await post('/v1/admin/demo/reset', { parcel_id: demo.hero }, ADMIN)

// 08 Tampered passport fails
const jwt = (await (await fetch(`${API}/v1/passports/${passportId}`)).json()).jwt
const [h, p, s] = jwt.split('.')
const payload = JSON.parse(Buffer.from(p, 'base64url').toString())
payload.credentialSubject.summary.flags = 0
const forged = [h, Buffer.from(JSON.stringify(payload)).toString('base64url'), s].join('.')
await d.goto(`${WEB}/verify`)
await d.getByTestId('jwt-input').fill(forged)
await d.getByTestId('verify-button').click()
await d.locator('[data-status="INVALID_SIGNATURE"]').waitFor()
await shot(d, '08-tamper', '01-invalid-signature', 'Tampered passport', 'Changing one field breaks the Ed25519 signature: INVALID SIGNATURE.')

// 09 Developers: page, API reference, Show API call
await d.goto(`${WEB}/developers`)
await settle(d, 1000)
await shot(d, '09-developers', '01-developers', 'Developers', 'Quickstart with curl, MCP set-up and how to verify passports independently.', { fullPage: true })
await d.goto(`${API}/docs`)
await settle(d, 4000)
await shot(d, '09-developers', '02-api-reference', 'Interactive API reference', 'OpenAPI 3.1 rendered with Scalar.')

// 10 Non-web proof: MCP, tests, defect gate, Postman (terminal cards)
const cards = [
  ['01-mcp', 'MCP: an AI agent calls Titlivo', 'uv run python -m titlivo.tools.mcp_demo', () => run('uv', ['run', '--directory', 'api', 'python', '-m', 'titlivo.tools.mcp_demo'])],
  ['02-defect-gate', 'Defect gate: planted vs detected', 'make check', () => run('uv', ['run', '--directory', 'api', 'python', '-m', 'titlivo.tools.check_defects'])],
  ['03-tests', 'Test suite', 'uv run pytest', () => run('uv', ['run', '--directory', 'api', 'pytest', '-q', '-p', 'no:warnings'])],
  ['04-postman', 'Postman collection (newman)', 'newman run postman/titlivo.postman_collection.json', () =>
    run('npx', ['-y', 'newman@6', 'run', 'postman/titlivo.postman_collection.json', '-e', 'postman/titlivo.local.postman_environment.json', '--env-var', `apiKey=${ADMIN}`, '--reporters', 'cli', '--color', 'off'])
      .replace(ADMIN, '***')],
]
const term = await desktop.newPage()
await term.setViewportSize({ width: 1440, height: 900 })
for (const [step, title, cmd, fn] of cards) {
  let text
  try {
    text = fn()
  } catch (e) {
    text = String(e.stdout ?? e)
  }
  await term.setContent(terminalHtml(title, `$ ${cmd}\n\n${text.trim().split('\n').slice(-40).join('\n')}`))
  await term.waitForTimeout(300)
  await shot(term, '10-proof', step, title, `Captured from the real command: ${cmd}`, { fullPage: true })
}

writeFileSync(resolve(OUT, 'manifest.json'), JSON.stringify({ generated_at: new Date().toISOString(), seed: 42, synthetic: true, shots: manifest }, null, 1))
console.log(`\n${manifest.length} screenshots → ${SHOTS}`)
await browser.close()
