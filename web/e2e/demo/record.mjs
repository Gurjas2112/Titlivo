// Screen recordings of the running app → demo-media/recordings/*.webm + chapters.txt
//   full-walkthrough: every flow, chapter cards, visible cursor, typed input
//   live-revocation:  split screen, admin injects F12 (left) → public verifier flips to SUSPENDED (right)
// Run: npm run demo:record   then   npm run demo:mp4
import { chromium } from '@playwright/test'
import { mkdirSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { API, CURSOR_SCRIPT, OUT, WEB, chapter, demoParcels, envKey, humanClick, humanType, post, run, terminalHtml } from './common.mjs'

const REC = resolve(OUT, 'recordings')
const RAW = resolve(REC, 'raw')
const ADMIN = envKey('ADMIN_API_KEY')
const SIZE = { width: 1920, height: 1080 }
rmSync(RAW, { recursive: true, force: true })
mkdirSync(RAW, { recursive: true })

const browser = await chromium.launch()
const demo = await demoParcels()
await post('/v1/admin/demo/reset', { parcel_id: demo.hero }, ADMIN)

async function newRecording() {
  const ctx = await browser.newContext({ viewport: SIZE, recordVideo: { dir: RAW, size: SIZE } })
  await ctx.addInitScript(CURSOR_SCRIPT)
  const page = await ctx.newPage()
  page.setDefaultTimeout(20_000)
  return { ctx, page, t0: Date.now() }
}

const pause = (page, ms) => page.waitForTimeout(ms)
async function scrollBy(page, dy, steps = 12) {
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, dy / steps)
    await page.waitForTimeout(60)
  }
}

function splitScreen(left, right, leftLabel, rightLabel) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#0b1736;font-family:Inter,system-ui,sans-serif}
  .wrap{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;padding:14px;height:100vh;box-sizing:border-box}
  .pane{display:flex;flex-direction:column;background:#fff;border-radius:14px;overflow:hidden}
  .lab{background:#14244f;color:#fff;font-size:15px;font-weight:600;padding:9px 14px}
  iframe{border:0;flex:1;width:100%}
  </style></head><body><div class="wrap">
  <div class="pane"><div class="lab">${leftLabel}</div><iframe name="left" src="${left}"></iframe></div>
  <div class="pane"><div class="lab">${rightLabel}</div><iframe name="right" src="${right}"></iframe></div>
  </div></body></html>`
}

// Passport for the hero parcel (issued through the UI in chapter 5; ensure one exists for the split screen).
async function heroPassportId() {
  const d = await (await fetch(`${API}/v1/parcels/${demo.hero}`)).json()
  return d.passports[0]?.id ?? (await post(`/v1/parcels/${demo.hero}/passports`)).id
}

// ------------------------------------------------------------------ full walkthrough
{
  const { ctx, page, t0 } = await newRecording()
  const chapters = []
  const mark = async (n, title, subtitle) => {
    chapters.push({ at: (Date.now() - t0) / 1000, title })
    await chapter(page, n, title, subtitle)
  }

  await page.goto(WEB)
  await pause(page, 2500)
  await mark(1, 'One parcel API across three states', 'Maharashtra 7/12, Karnataka RTC and Gujarat 7/12 + 8-A: different scripts, units and words, one schema.')
  await humanType(page, page.getByTestId('search-input'), 'नितीन भोसले')
  await page.keyboard.press('Enter')
  await pause(page, 3000)
  await humanType(page, page.getByTestId('search-input'), '214/2')
  await humanClick(page, page.getByTestId('search-button'))
  await pause(page, 3000)
  await humanClick(page, page.getByTestId('result').filter({ hasText: 'Sahyagaon' }).first())
  await pause(page, 3500)

  await mark(2, 'The dossier: canonical and native, side by side', 'Facts come from SQL. The record is kept exactly as the state wrote it.')
  await pause(page, 2000)
  await humanClick(page, page.getByRole('button', { name: /Native record/ }))
  await pause(page, 3500)
  await humanClick(page, page.getByRole('button', { name: /Canonical/ }))
  await pause(page, 1500)
  await scrollBy(page, 700)
  await pause(page, 3500)
  await scrollBy(page, -700)

  await mark(3, 'Red flags in plain language', 'Nine SQL rules, including Fraud Sentinel patterns from real cases. 100 % recall on planted defects.')
  for (const id of ['F12', 'F11', 'F16']) {
    await page.goto(`${WEB}/p/${demo[id]}`)
    await pause(page, 2500)
    const card = page.getByTestId(`flag-${id}`).first()
    await card.scrollIntoViewIfNeeded()
    await pause(page, 1500)
    await humanClick(page, card.getByRole('button', { name: /evidence/ }))
    await pause(page, 3500)
  }

  await mark(4, 'Ask the property', 'Answers use only facts from the records, are checked number by number, and never say "safe".')
  await page.goto(`${WEB}/p/${demo.F02}`)
  await pause(page, 2000)
  await page.getByTestId('ask').scrollIntoViewIfNeeded()
  await humanClick(page, page.getByRole('button', { name: 'Is there a loan on this land?' }))
  await page.getByTestId('answer').waitFor()
  await pause(page, 4500)

  await mark(5, 'Issue a Title Passport', 'A signed W3C Verifiable Credential. No names inside. Verifiable by anyone, by QR, link or API.')
  await page.goto(`${WEB}/p/${demo.hero}`)
  await pause(page, 2500)
  await page.getByTestId('passport-card').scrollIntoViewIfNeeded()
  const issue = page.getByTestId('issue-passport')
  if (await issue.isVisible()) await humanClick(page, issue)
  await page.getByTestId('passport-card').getByTestId('status-pill').waitFor()
  await pause(page, 3000)
  const pid = await heroPassportId()
  await page.goto(`${WEB}/v/${pid}`)
  await page.getByTestId('status-pill').waitFor()
  await pause(page, 4000)

  await mark(6, 'A title check that stays alive', 'A fake-heir transfer reaches the registry. Watch the passport on the right.')
  await page.setContent(splitScreen(`${WEB}/admin`, `${WEB}/v/${pid}`, 'Admin · inject a registry event', 'Public verifier · what the bank sees'))
  await pause(page, 3500)
  const admin = page.frameLocator('iframe[name=left]')
  const verifier = page.frameLocator('iframe[name=right]')
  await humanType(page, admin.getByTestId('admin-key'), ADMIN)
  await admin.getByTestId('admin-parcel').fill(demo.hero)
  await pause(page, 1200)
  await humanClick(page, admin.getByTestId('preset-heir_impersonation'))
  await verifier.locator('[data-status="SUSPENDED"]').waitFor({ timeout: 15000 })
  await pause(page, 5000)
  await post('/v1/admin/demo/reset', { parcel_id: demo.hero }, ADMIN)
  await verifier.locator('[data-status="LIVE"]').waitFor({ timeout: 15000 })
  await pause(page, 2000)

  await mark(7, 'Tamper-proof', 'Change one field in the passport and the Ed25519 signature no longer verifies.')
  const jwt = (await (await fetch(`${API}/v1/passports/${pid}`)).json()).jwt
  const [h, p, s] = jwt.split('.')
  const payload = JSON.parse(Buffer.from(p, 'base64url').toString())
  payload.credentialSubject.summary.flags = 0
  await page.goto(`${WEB}/verify`)
  await pause(page, 1500)
  await page.getByTestId('jwt-input').fill([h, Buffer.from(JSON.stringify(payload)).toString('base64url'), s].join('.'))
  await humanClick(page, page.getByTestId('verify-button'))
  await page.locator('[data-status="INVALID_SIGNATURE"]').waitFor()
  await pause(page, 4000)

  await mark(8, 'For developers and AI agents', 'REST with curl and Postman, OpenAPI docs, and an MCP server any AI agent can call.')
  await page.goto(`${WEB}/developers`)
  await pause(page, 3000)
  await scrollBy(page, 600)
  await pause(page, 3000)
  await page.goto(`${API}/docs`)
  await pause(page, 5000)
  const mcp = run('uv', ['run', '--directory', 'api', 'python', '-m', 'titlivo.tools.mcp_demo'])
  await page.setContent(terminalHtml('MCP: an AI agent calls Titlivo', `$ uv run python -m titlivo.tools.mcp_demo\n\n${mcp.trim()}`))
  await pause(page, 7000)

  chapters.push({ at: (Date.now() - t0) / 1000, title: 'Close' })
  await page.goto(WEB)
  await chapter(page, '', 'Diligence done once, verifiable by anyone, and alive.', 'Titlivo · github.com/Gurjas2112/Titlivo · all data synthetic · not a legal opinion', 5000)

  const video = page.video()
  await ctx.close()
  renameSync(await video.path(), resolve(REC, 'full-walkthrough.webm'))
  const fmt = (t) => `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}`
  writeFileSync(resolve(REC, 'chapters.txt'), ['00:00 Intro', ...chapters.map((c) => `${fmt(c.at)} ${c.title}`)].join('\n') + '\n')
  writeFileSync(resolve(REC, 'chapters.json'), JSON.stringify(chapters, null, 1))
  console.log('✓ full-walkthrough.webm', fmt((Date.now() - t0) / 1000))
}

// ------------------------------------------------------------------ live revocation (split screen)
{
  const { ctx, page } = await newRecording()
  const pid = await heroPassportId()
  await page.goto(WEB)
  await page.setContent(splitScreen(`${WEB}/admin`, `${WEB}/v/${pid}`, 'Registry event arrives (admin demo)', 'Public verifier · scanned from the QR'))
  await chapter(page, '', 'A title check that stays alive', 'Survey 214/2, Sahyagaon · Title Passport is LIVE. Then a fake-heir sale is registered.', 3000)
  await pause(page, 2500)
  const admin = page.frameLocator('iframe[name=left]')
  const verifier = page.frameLocator('iframe[name=right]')
  await humanType(page, admin.getByTestId('admin-key'), ADMIN)
  await admin.getByTestId('admin-parcel').fill(demo.hero)
  await pause(page, 1500)
  await humanClick(page, admin.getByTestId('preset-heir_impersonation'))
  await verifier.locator('[data-status="SUSPENDED"]').waitFor({ timeout: 15000 })
  await pause(page, 6000)
  const video = page.video()
  await ctx.close()
  renameSync(await video.path(), resolve(REC, 'live-revocation.webm'))
  await post('/v1/admin/demo/reset', { parcel_id: demo.hero }, ADMIN)
  console.log('✓ live-revocation.webm')
}

await browser.close()
rmSync(RAW, { recursive: true, force: true })
