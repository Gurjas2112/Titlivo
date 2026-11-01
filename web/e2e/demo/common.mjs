// Shared helpers for demo media capture (screenshots + recordings). Captured from the running app,
// never hand-edited. Requires: API on :8000, web on :5173, data loaded with seed 42.
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
export const OUT = resolve(ROOT, 'demo-media')
export const WEB = process.env.DEMO_WEB ?? 'http://localhost:5173'
export const API = process.env.DEMO_API ?? 'http://localhost:8000'

export function envKey(name) {
  const line = readFileSync(resolve(ROOT, '.env'), 'utf8')
    .split(/\r?\n/)
    .find((l) => l.startsWith(name + '='))
  return line ? line.slice(name.length + 1).replace(/^'|'$/g, '') : ''
}

export async function demoParcels() {
  return (await fetch(`${API}/v1/demo/parcels`)).json()
}

export async function post(path, body, key) {
  const r = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  return r.json()
}

/** Run a command and return its stdout (used for the terminal cards). */
export function run(cmd, args, cwd = ROOT) {
  return execFileSync(cmd, args, {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PYTHONUTF8: '1', FORCE_COLOR: '0' },
    shell: true,
    stdio: ['ignore', 'pipe', 'pipe'], // no inherited stdin: child processes must not wait on it
    timeout: 180_000,
  })
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;')

/** A terminal-style card for non-web proof (MCP calls, test runs, Postman). */
export function terminalHtml(title, text) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#e9edf5;font-family:Inter,system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:56px 0 32px;box-sizing:border-box}
  .t{width:1280px;background:#0b1736;border-radius:16px;box-shadow:0 20px 60px #0b173640;overflow:hidden}
  .bar{display:flex;gap:8px;align-items:center;padding:14px 18px;background:#14244f;color:#c7d2fe;font-size:14px}
  .d{width:12px;height:12px;border-radius:50%}
  pre{margin:0;padding:22px 26px;color:#e2e8f0;font:14px/1.6 'JetBrains Mono',Consolas,monospace;white-space:pre-wrap}
  .ok{color:#2ec4a6}.hi{color:#ff7a00}
  .rib{position:fixed;top:0;left:0;right:0;background:#ff7a00;color:#fff;text-align:center;font:600 12px Inter,sans-serif;padding:4px}
  </style></head><body><div class="rib">Synthetic data · Titlivo prototype</div><div class="t"><div class="bar">
  <span class="d" style="background:#ff5f57"></span><span class="d" style="background:#febc2e"></span><span class="d" style="background:#28c840"></span>
  <span style="margin-left:10px">${esc(title)}</span></div><pre>${esc(text)
    .replace(/(√|✓|PASS|ALL PASS|passed)/g, '<span class="ok">$1</span>')
    .replace(/(\[F\d\d\] HIGH)/g, '<span class="hi">$1</span>')}</pre></div></body></html>`
}

/** Big chapter title card injected over the page during recordings. */
export async function chapter(page, n, title, subtitle = '', ms = 2600) {
  await page.evaluate(
    ([n, title, subtitle]) => {
      const d = document.createElement('div')
      d.id = '__chapter'
      d.style.cssText =
        'position:fixed;inset:0;z-index:99999;background:#0b1736;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:Inter,sans-serif;transition:opacity .4s'
      d.innerHTML = `<div style="color:#ff7a00;font-weight:600;letter-spacing:.2em;font-size:18px">CHAPTER ${n}</div>
        <div style="font-size:56px;font-weight:700;margin-top:12px;text-align:center;max-width:1400px">${title}</div>
        <div style="font-size:22px;margin-top:16px;color:#cbd5e1;max-width:1200px;text-align:center">${subtitle}</div>
        <div style="position:absolute;bottom:24px;font-size:13px;color:#94a3b8">Titlivo · synthetic demonstration data</div>`
      document.body.appendChild(d)
    },
    [n, title, subtitle],
  )
  await page.waitForTimeout(ms)
  await page.evaluate(() => {
    const d = document.getElementById('__chapter')
    if (d) {
      d.style.opacity = '0'
      setTimeout(() => d.remove(), 400)
    }
  })
  await page.waitForTimeout(450)
}

/** Visible cursor dot + click ripple, so viewers can follow the pointer in recordings. */
export const CURSOR_SCRIPT = `
window.addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.style.cssText='position:fixed;z-index:100000;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;background:rgba(255,122,0,.55);border:2px solid #fff;box-shadow:0 0 0 2px rgba(11,23,54,.35);pointer-events:none;transition:transform .08s;left:-50px;top:-50px';
  document.body.appendChild(c);
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  document.addEventListener('mousedown', () => c.style.transform = 'scale(.7)', true);
  document.addEventListener('mouseup', () => c.style.transform = 'scale(1)', true);
});`

/** Move the mouse visibly to an element and click it. */
export async function humanClick(page, locator, opts = {}) {
  const box = await locator.boundingBox()
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 25 })
    await page.waitForTimeout(250)
  }
  await locator.click(opts)
}

export async function humanType(page, locator, text) {
  await humanClick(page, locator)
  await locator.fill('')
  await locator.pressSequentially(text, { delay: 90 })
}
