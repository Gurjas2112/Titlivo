// .webm → H.264 MP4 (plays everywhere), plus one clip per chapter of the full walkthrough.
// Run: npm run demo:mp4   (needs ffmpeg on PATH)
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { OUT } from './common.mjs'

const REC = resolve(OUT, 'recordings')
const H264 = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an']
const ff = (args) => execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...args], { stdio: 'inherit' })

for (const name of ['full-walkthrough', 'live-revocation']) {
  const src = resolve(REC, `${name}.webm`)
  if (!existsSync(src)) continue
  ff(['-i', src, ...H264, resolve(REC, `${name}.mp4`)])
  console.log('✓', `${name}.mp4`)
}

const chaptersFile = resolve(REC, 'chapters.json')
if (existsSync(chaptersFile)) {
  const chapters = JSON.parse(readFileSync(chaptersFile, 'utf8'))
  mkdirSync(resolve(REC, 'flows'), { recursive: true })
  chapters.slice(0, -1).forEach((c, i) => {
    const slug = `${String(i + 1).padStart(2, '0')}-${c.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`
    ff(['-ss', c.at.toFixed(2), '-to', chapters[i + 1].at.toFixed(2), '-i', resolve(REC, 'full-walkthrough.mp4'), ...H264, resolve(REC, 'flows', `${slug}.mp4`)])
    console.log('  ✓ flows/' + slug + '.mp4')
  })
}
