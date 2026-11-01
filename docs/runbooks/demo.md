# Demo runbook: "a title check that stays alive" (3 minutes)

## Before the meeting (5 minutes)

```bash
make db                      # PostGIS on :54329 (Docker must be running)
make api                     # API on :8000
cd web && npm run dev        # web on :5173
```

Check: http://localhost:8000/healthz/db shows `"parcels": 270`. Copy `ADMIN_API_KEY` from `.env`.

Open three browser tabs:

1. http://localhost:5173 (home)
2. http://localhost:5173/admin (paste the admin key; it stays for the session)
3. Leave the third for the verifier.

If anything was injected earlier, press **Reset demo** on the admin page first.

## The script

| Time | Say | Do |
|---|---|---|
| 0:00 | "Every bank re-runs title checks on the same land, and the report is stale the day it's printed. In March, Hyderabad police caught a gang re-registering plots with forged death certificates and fake heirs." | Home page |
| 0:20 | "Three states, three formats. One search box in any script." | Search `नितीन भोसले`, then `214/2`; open Sahyagaon |
| 0:35 | "One schema, but the record as the state wrote it is never thrown away." | Toggle **Native record** (Marathi keys, Devanagari numerals, hectare-are) |
| 0:50 | "Facts come from SQL, not from a model. Here is the fake-heir pattern caught on another parcel." | Home → red-flag chip **F12 Fake heirs**; show the timeline's "no death record" and the flag card's evidence |
| 1:10 | "Ask it in plain language. Every number is checked against the records before it is shown." | On the F02 parcel: **Is there a loan on this land?** |
| 1:25 | "Now the differentiator: turn this check into a credential anyone can verify." | Survey 214/2 → **Issue Title Passport** → **Open public verifier** (tab 3, or scan the QR with a phone on the same network) |
| 1:45 | "A fake-heir sale reaches the registry." | Tab 2: **Sale by newly added heirs** → switch to tab 3: it flips to **SUSPENDED** within seconds |
| 2:10 | "Tamper with one field and the signature fails." | Download the `.jwt`, edit a character, drop it on **Verify a passport** |
| 2:25 | "For developers: one API, Postman, and an MCP server any AI agent can call." | Developers page → `/docs` → terminal: `uv run --directory api python -m titlivo.tools.mcp_demo` |
| 2:45 | "Diligence done once, verifiable by anyone, and alive." | — |

## After

Press **Reset demo** on the admin page (removes injected events and reinstates passports).

## If something goes wrong

- Map tiles blank: the basemap needs internet. Parcels and everything else still work.
- Verifier stuck: reload; status is re-checked on every load.
- Fallback: play `demo-media/recordings/full-walkthrough.mp4` or the 25-second `live-revocation.mp4` from the [GitHub release](https://github.com/Gurjas2112/Titlivo/releases/tag/demo-media-v1).

## Regenerating demo media

With the API and web running and data loaded with seed 42:

```bash
cd web
npm run demo:shots    # 33 screenshots → demo-media/screenshots + manifest.json
npm run demo:verify   # rejects blank or duplicate screenshots
npm run demo:record   # full walkthrough + split-screen live revocation (.webm)
npm run demo:mp4      # H.264 MP4s + one clip per chapter (needs ffmpeg)
```
