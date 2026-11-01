# Titlivo v2.0 — Build Prompt for GitHub Copilot (coding agent)

![Titlivo](brand/titlivo-lockup-light.png)

> **How to use this file**
> - Save it as `.github/copilot-instructions.md` **and** `AGENTS.md` in the repo root.
> - Keep `docs/Titlivo_Engineering_Specification_v2.0.md` in the repo. This file is the build contract; the specification has the reasoning. **If they disagree, the specification wins.**
> - One milestone per issue/PR ("Implement Milestone 8 from AGENTS.md"). Never attempt the whole system at once.

---

## 1. Role and goal

You are a senior Python, SQL/PostGIS and TypeScript engineer building **Titlivo** (*title* + *vivo*, "alive": a land title that stays alive). It is **one canonical parcel API across three Indian states** (Maharashtra 7/12, Karnataka RTC, Gujarat 7/12 + 8-A) with:
- deterministic **title chain and red flags** computed in SQL;
- a **cited "Ask the Property" agent** (Pydantic AI + Gemini 3.8 Flash) over parcel tools and a **land-law knowledge base** (hybrid RAG);
- **vector map tiles**;
- a **FastMCP server** so external AI agents can query parcels;
- **Title Passports**: W3C Verifiable Credential 2.0 (`vc+jwt`, EdDSA) with **live status** via a Bitstring Status List, publicly verifiable by QR/link/API;
- **Fraud Sentinel** rules F11–F16 and **living monitoring** that suspends passports and notifies lenders through a Postgres **transactional outbox**.

It is a land-records prototype and a portfolio piece for a Solutions Engineer role. The same parcel must be demo-able to a buyer, a bank officer and a developer.

**Prototype scope (do not exceed):** states MH (LGD 27), KA (29), GJ (24); 6 villages per state with real polygons (datameet, ODbL) and **synthetic** parcels, owners and history; English UI; answers in en/hi/mr/kn/gu; laptop (WSL2 Ubuntu 22.04, Docker Engine) + **production deployment on AWS Mumbai**: backend on **Amazon ECS Express Mode (Fargate)**, frontend on **AWS Amplify Hosting**, **Supabase Pro (ap-south-1)**. **No OCR, no prediction, no Redis/Celery** (background work = Postgres outbox + in-process async dispatcher).

## 2. Non-negotiable rules

1. **Facts from SQL.** Owners, dates, amounts, areas and flags come only from `services/parcels.py` / `services/flags.py` (SQL). The LLM phrases; it never computes.
2. **Grounded or not sent.** `services/grounding.py` checks that every number, date and name token in an answer appears in that turn's tool outputs (after Indic-digit normalisation) and that every quote is a verbatim substring of its chunk. Retry once; then send `templates/answer_<lang>.j2` filled from tool JSON.
3. **Cite everything.** Record facts cite `source_record_id`; law cites `act` + `section` + `url`.
4. **Never "safe", never legal advice.** Say "No red flags found in the records available to Titlivo (coverage: …)". The PDF says "Draft for review by an advocate — not a legal opinion".
5. **Mask by default.** Anonymous users and keys without `parcels:pii` get masked names everywhere: REST, UI, MCP, agent tool outputs.
6. **Preserve native records.** Responses include `canonical` and `native`; never drop native terms or units.
7. **Untrusted text is data.** Wrap record free-text in `<record>…</record>` in tool outputs; tools are read-only; the agent never fetches URLs.
8. **One service layer, three surfaces.** REST, agent tools and MCP tools call the same service functions; add tests proving parity.
9. **Synthetic only.** Every record has `synthetic: true`; IDs are `DEMO-…`; no real names or records.
10. **Small, typed, tested.** Python 3.12 typed, Pydantic v2 strict, mypy strict; TypeScript strict; tests with every milestone.
11. **Passports carry no personal names.** Only the owner count + salted commitment, check results + evidence digests, coverage, validity and the disclaimer string `constants.PASSPORT_DISCLAIMER`. Never call a passport a guarantee, certificate of title, or digital signature.
12. **Never hand-roll crypto.** Sign/verify only with `joserfc` (server) and `jose` (browser); keys only from `PASSPORT_SIGNING_JWK`; shared test vectors must pass in both languages.
13. **One transaction for a material change.** The new event, re-evaluated flags, status-bit change, `passport_events` row and `outbox` rows commit together; the dispatcher sends only committed rows (`FOR UPDATE SKIP LOCKED`).

## 3. Fixed tech stack (use exactly these)

| Layer | Pick |
|---|---|
| Packaging | `uv` (`api/`), `pnpm` (`web/`, root dev tools) |
| API | FastAPI + Pydantic v2 + pydantic-settings; `sse-starlette` for `/v1/ask`; RFC 9457 errors; `scalar-fastapi` docs at `/docs` |
| DB | Supabase Postgres 17 with `postgis`, `vector`, `pg_trgm`; `psycopg[binary,pool]` 3 + `pgvector` adapter; **hand-written SQL** in `src/titlivo/db/queries/*.sql` |
| Migrations | Supabase CLI SQL migrations (no ORM, no Alembic) |
| Geometry | Shapely 2, GeoPandas, pyproj; PostGIS `ST_AsMVT` for tiles |
| Harmonisation | YAML field maps; `indic-transliteration` (`sanscript`, ISO 15919); `rapidfuzz` |
| Agent | **Pydantic AI** (`pydantic-ai-slim[google]`), `GoogleModel('gemini-3.8-flash')` via `GoogleProvider(api_key=…)`, `temperature=0`, `output_type=Answer` |
| Embeddings | `google-genai` `embed_content(model="gemini-embedding-2", config=EmbedContentConfig(output_dimensionality=768))` |
| KB ingest | **Docling** (`DocumentConverter` + `HybridChunker`, max 512 tokens), PyTorch CUDA in WSL on the RTX 3060 (dependency group `ingest`, excluded from the production image) |
| Retrieval | pgvector HNSW cosine top-40 + Postgres FTS (`simple`, `websearch_to_tsquery`) top-40 → RRF k=60 → top-8 |
| MCP | **FastMCP 3**: `mcp.http_app(path="/")`, mounted at `/mcp`, lifespans combined with `fastmcp.utilities.lifespan.combine_lifespans` |
| Auth | Supabase Auth (email+password, Google, TOTP for admin); PyJWT `PyJWKClient` on JWKS; API keys `tlv_live_…` (SHA-256) with scopes |
| Rate limit | `slowapi` (anon per IP, user, key) |
| PDF | WeasyPrint + `staticmap` for the map image |
| Frontend | Vite + React 19 + TS + Tailwind v4 + shadcn/ui; React Router; TanStack Query; **MapLibre GL JS** with OpenFreeMap `liberty` style; Recharts; `@fontsource/noto-sans-{devanagari,kannada,gujarati}` |
| Telemetry | structlog JSON; OpenTelemetry (FastAPI, psycopg, httpx) + custom GenAI spans → OTLP |
| Evals | **promptfoo** (RAG, agent, red team) |
| Tests | pytest, pytest-asyncio, Hypothesis, httpx `AsyncClient`, FastMCP in-memory client, Playwright, Locust, Vitest (browser verifier) |
| Credentials | W3C VC 2.0 + VC-JOSE-COSE (`typ: vc+jwt`, `alg: EdDSA`, Ed25519), issuer `did:web`, Bitstring Status List v1.0 (131,072 entries, gzip + base64url, purposes `suspension` and `revocation`); `joserfc` server-side, `jose` + `DecompressionStream` in the browser; `qrcode` (SVG) |
| Delivery | Postgres `outbox` + asyncio dispatcher in the FastAPI lifespan; `standardwebhooks`; `resend` (prod) / Mailpit (dev) |
| Production | **ECR** → **ECS Express Mode** (`create/update-express-gateway-service`, 0.5 vCPU / 1 GB, min 1 / max 3 tasks, health `/healthz`) · **Amplify Hosting** (`amplify.yml`, SPA rewrite, `customHttp.yml` security headers) · **Secrets Manager** · **GitHub Actions OIDC** · Supabase **Pro** via the transaction pooler (port 6543, psycopg `prepare_threshold=None`) |

## 4. Repository layout

```
titlivo/
├── AGENTS.md  .github/copilot-instructions.md  README.md  Makefile  .env.example  .env.prod.example
├── .github/workflows/{ci.yml,deploy.yml}
├── docs/{Titlivo_Engineering_Specification_v1.0.md,quickstart.md,mcp.md,integrate-lender.md,
│         security-faq.md,model-card.md,errors.md,adr/,runbooks/{demo.md,incident.md,breach.md}}
├── config/{field_maps/{mh_712,ka_rtc,gj_712}.yaml, glossary/*.csv, flags.yaml, prompts/system.md}
├── kb/SOURCES.yaml
├── templates/{answer_en.j2,answer_hi.j2,answer_mr.j2,answer_kn.j2,answer_gu.j2,title_draft.html.j2}
├── api/
│   ├── pyproject.toml uv.lock
│   ├── src/titlivo/
│   │   ├── main.py settings.py telemetry.py logging.py constants.py
│   │   ├── auth/{jwt.py,api_keys.py,deps.py,masking.py}
│   │   ├── db/{pool.py,sql.py,queries/*.sql}
│   │   ├── adapters/{base.py,mh_712.py,ka_rtc.py,gj_712.py}
│   │   ├── services/{units.py,translit.py,glossary.py,harmonise.py,parcels.py,title_chain.py,flags.py,
│   │   │             kb_search.py,grounding.py,agent.py,answer_cache.py,reports.py,bulk.py,tiles.py,usage.py,
│   │   │             sentinel.py,did.py,passport.py,passport_verify.py,status_list.py,monitor.py,shares.py,outbox.py}
│   │   ├── mcp_server.py
│   │   ├── routers/{parcels.py,ask.py,law.py,reports.py,glossary.py,coverage.py,tiles.py,admin.py,health.py,demo.py,
│   │   │            passports.py,status.py,wellknown.py,shares.py,subscriptions.py,events.py}
│   │   └── tools/{lgd_load.py,villages_load.py,synth.py,ingest.py,kb_download.py,kb_ingest.py,check_defects.py}
│   └── tests/{unit,adapters,sql,api,mcp,agent}/...
├── evals/promptfoo/{rag.yaml,agent.yaml,redteam.yaml,datasets/*.csv}
├── sql/demo/*.sql
├── web/ (src/{routes,components/map,components/dossier,components/ask,components/passport,lib/verifyPassport.ts,api,i18n},
│         public/{favicon.ico,apple-touch-icon.png,og.png,icons/icon-192.png,icons/icon-512.png,manifest.webmanifest}, e2e/)
├── brand/ (icon SVG/PNGs, lockups, social preview, BRAND.md)
├── tests/vectors/passport/*.json   (shared Python + TS crypto test vectors)
├── notebooks/{01_bank_officer_story.ipynb,02_sql_insights.ipynb,03_verify_a_passport.ipynb}
├── demo-media/{manifest.json,metrics.json,screenshots/<NN-flow>/<NN-step>.png,recordings/,video/}   (recordings/*.webm git-ignored; MP4s published as release assets)
├── docs/demo-coverage.yaml   (C01–C65: the single source of truth for what demo media must show)
├── web/e2e/demo/{flows/01-onboarding-and-access.spec.ts … 19-live-deployment.spec.ts, walkthrough.spec.ts, cursor.ts, manifest.ts, capture-nonweb.ts, verify-coverage.ts}
├── video/   (Remotion: src/{index.ts,Root.tsx,scenes/*.tsx,rig/Peep.tsx,fx/{Grain,Letterbox,LightLeak,Shockwave,JourneyPath,PhoneFrame}.tsx};
│            assets/{backgrounds/prompts.yaml,characters.yaml}; public/{bg,vo,peeps}; tools/{gen_backgrounds.py,tts.py,peeps.ts})
├── voice/script.yaml   (scene, speaker, language, description, text, subtitle)
├── amplify.yml  customHttp.yml
├── postman/titlivo.postman_collection.json
├── supabase/{config.toml,seed.sql,migrations/*.sql,shared/auth_hook.sql}
├── scripts/{migrate_cloud.sh,demo.sh}
└── infra/{Dockerfile.api,Dockerfile.local,docker-compose.dev.yml,grafana/titlivo.json,aws/{deploy-role-trust.json,deploy-role-policy.json,exec-secrets-policy.json}}
```

## 5. Environment variables

```dotenv
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
GOOGLE_API_KEY=
LLM_MODEL=gemini-3.8-flash
LLM_MODE=live            # live | mock (recorded responses for CI/e2e)
EMBED_MODEL=gemini-embedding-2
EMBED_DIM=768
LLM_TIMEOUT_S=20
DAILY_LLM_BUDGET_USD=2
PROMPT_VERSION=2026-10-30.1
APP_ENV=dev
DEMO_LOGIN=true
CORS_ORIGINS=http://localhost:5173
OTEL_SERVICE_NAME=titlivo-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
PUBLIC_API_BASE=http://localhost:8000
ISSUER_DID=did:web:localhost%3A8000
PASSPORT_SIGNING_JWK=
PASSPORT_VALIDITY_DAYS=90
STATUS_LIST_SIZE=131072
OUTBOX_POLL_SECONDS=2
WEBHOOK_SECRET_KEY=
EMAIL_MODE=mailpit
RESEND_API_KEY=
```
`make keys` generates a local Ed25519 JWK (`joserfc.jwk.OKPKey.generate_key('Ed25519')`) into `.env`; production keys live only in Secrets Manager.
Web: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`, `VITE_MAP_STYLE=https://tiles.openfreemap.org/styles/liberty`.

## 6. Data and harmonisation

- **Synthetic generator** (`tools/synth.py`, `SEED` env): Voronoi parcels clipped to village polygons; survey numbers in state style; 30-year event histories; planted defects at the spec 6.1 rates written to `data/truth/defects.csv`; native JSON per state in local-script keys, terms and units.
- **Adapters** implement `StateAdapter.parse()` and `to_canonical()` (spec 6.1) driven by `config/field_maps/*.yaml`. The canonical bundle has parcel, parties, holdings, title_events, encumbrances, litigation and source_record.
- **Units** (`units.py`): `hectare_are`, `hectare_are_sqm`, `acre_gunta` (1 acre = 40 guntas = 4046.856 m²), `sq_yd`, `sq_ft` → m². Property-test the round trips.
- **Transliteration** (`translit.py`): ISO 15919 Latin + `name_key` (lower-case, diacritics stripped, long vowels folded); trigram index for search.
- **Glossary** (`glossary.py`): load CSVs into `titlivo.term_glossary`; `map_term(domain, state, local_term) -> canonical_code`; unknown terms pass through and are logged to `ingest_issues`.
- **Ingest validation:** valid geometry, inside village, area within ±10 % of geodesic area (else F04 data), shares sum to 1, monotonic dates, LGD hierarchy.
- **Demo ULPIN:** `DEMO-` + 14 chars (2-digit state code + 12-char base-32 geohash of the centroid).

## 7. Title chain and flags

- `sql/title_chain.sql`: recursive CTE ordered by `registered_on`, carrying the holder set; outputs `consistent` per event.
- `config/flags.yaml` defines F01–F10 (spec 6.2) with `severity`, `sql` (file reference) and `template` in en and hi. `services/flags.py` runs them and returns `Flag{id, severity, text, evidence, source_record_id}`.
- `tools/check_defects.py` compares planted defects with detected flags: **recall 100 %, precision ≥ 98 %** or exit non-zero (CI gate).
- `sql/demo/*.sql`: 10 readable storytelling queries with comments (for the interview).

## 8. Knowledge base and agent

- `tools/kb_download.py` fetches files listed in `kb/SOURCES.yaml` (URL, act, state_code, section regex) into `data/kb/` and records SHA-256 and the date.
- `tools/kb_ingest.py`: Docling convert → HybridChunker → parse section numbers → embed (768-d, batch, retry) → insert `kb.chunks`.
- `services/kb_search.py`: hybrid search + RRF + state boost; returns `Chunk{act, section, url, text, score}`.
- `services/agent.py`:
  - Pydantic AI `Agent(GoogleModel(settings.llm_model, provider=GoogleProvider(api_key=…)), output_type=Answer, system_prompt=load('config/prompts/system.md'))`.
  - Tools: `search_parcels`, `get_parcel_dossier`, `get_title_chain`, `list_red_flags`, `explain_term`, `search_land_law`. Each tool receives a `CallerContext` (role, scopes) via Pydantic AI deps for masking.
  - `Answer = {text, language, claims[{text, source_ids}], citations[{kind, ref, url?, quote?}], follow_ups[]}`.
  - Run → `grounding.check` → retry once with violations → template fallback. Record tokens and cost.
- `routers/ask.py`: SSE events `token`, `citation`, `done{grounded, model, prompt_version, coverage}`, `error`. Answer cache keyed by `sha256(question_norm, parcel_id, parcel.version, language)`, TTL 24 h.
- `LLM_MODE=mock` serves recorded `Answer` JSON from `tests/fixtures/llm/` (CI and e2e).

## 9. MCP server (`mcp_server.py`)

```python
from fastmcp import FastMCP
mcp = FastMCP("titlivo")

@mcp.tool()
async def get_title_chain(parcel_id: str, since_year: int = 1996) -> TitleChain:
    """Ordered ownership and encumbrance events for one parcel, each with its source record id.
    Names are masked unless the API key has scope parcels:pii."""
    ctx = current_caller()            # set by the /mcp auth middleware
    return await title_chain.get(parcel_id, since_year, ctx)
```
- Same six tools as the agent, docstrings written for agents, Pydantic return types.
- `main.py`: `mcp_app = mcp.http_app(path="/")`; `app = FastAPI(lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan))`; `app.mount("/mcp", mcp_app)`.
- ASGI middleware for `/mcp`: require `Authorization: Bearer tlv_…` with scope `mcp`; 401 problem+json otherwise; set the caller context; count `mcp.call` metrics.
- `docs/mcp.md`: MCP Inspector walkthrough (`npx @modelcontextprotocol/inspector`, transport Streamable HTTP, URL, header).

## 9a. Fraud Sentinel (`services/sentinel.py`)

Rules F11–F16 exactly as spec 6.11 (double sale, heir-impersonation transfer, registration–revenue mismatch, GPA chain, dormant-parcel activation, sale while mortgaged). Each rule is a SQL file in `db/queries/sentinel/` with a YAML entry in `config/flags.yaml` (severity, template en/hi, material: true). The synthetic generator plants each pattern; `check_defects` covers F01–F16 (recall 100 %, precision ≥ 98 %).

## 9b. Title Passport (`services/passport.py`, `passport_verify.py`, `status_list.py`, `did.py`)

- `GET /.well-known/did.json`: DID document for `ISSUER_DID` with all public Ed25519 keys (`JsonWebKey`), current and retired.
- `issue(parcel_id, profile, caller) -> Passport`: build the credential exactly per spec 6.10 (no names; `owners.commitment = sha256(salt‖sorted(name_key))`; `evidenceDigest` = sha256 of canonical JSON of the evidence rows; `validUntil = now + PASSPORT_VALIDITY_DAYS`), allocate a random free index in the active suspension and revocation lists, sign as JWS compact with header `{alg: "EdDSA", typ: "vc+jwt", kid}`, store, and return `{id, jwt, qr_svg, verify_url}`.
- `status_list.py`: bitstring in `bytea` (131,072 bits), `set_bit(list_id, index, value)` inside the caller's transaction, `credential(list_id)` → signed `BitstringStatusListCredential` (`encodedList` = base64url(gzip(bits))), cached in the row and re-signed on change; `GET /status/{id}` with `Cache-Control: public, max-age=60` and an `ETag`.
- `passport_verify.py` and `web/src/lib/verifyPassport.ts`: the algorithm in spec 6.10 returning `LIVE | SUSPENDED | REVOKED | EXPIRED | INVALID_SIGNATURE` + reasons; both must pass `tests/vectors/passport/*.json` (valid, tampered payload, wrong kid, expired, suspended bit, revoked bit).
- Reissue: create a new passport, set the old one's revocation bit, link `superseded_by`.

## 9c. Monitoring, sharing and delivery (`monitor.py`, `shares.py`, `outbox.py`)

- `POST /v1/admin/events` (admin, aal2) ingests a registration or revenue event (and powers the "Inject registry event" demo presets). In **one transaction**: insert the event → re-run F01–F16 for the parcel → if material (spec 6.10) set the suspension bit for every active passport of the parcel, insert `passport_events`, enqueue `outbox` rows (`passport.suspended` to subscribed lenders, e-mail to the owner) → commit.
- `outbox.py`: `async def run_dispatcher()` started in the FastAPI lifespan; every `OUTBOX_POLL_SECONDS` select ≤ 50 due rows `FOR UPDATE SKIP LOCKED`, deliver (Standard Webhooks signing with the subscription secret, decrypted with Fernet), set `delivered_at` or `attempts+1` and `next_attempt_at` by backoff 30 s, 2 m, 10 m, 1 h, 6 h; hourly: expire passports and refresh status-list credentials. Graceful shutdown on SIGTERM (ECS stops tasks with SIGTERM).
- `GET /v/{id}/events` (SSE): pushes status changes for an open verifier page (`LISTEN/NOTIFY` on channel `passport_status`).
- `shares.py`: share grants (owner only, purpose enum, expiry ≤ 30 days, revoke) + append-only `consent_receipts`; a lender may read the full dossier and create subscriptions only while a grant is valid.

## 10. REST API (implement exactly; see spec Annexure A)

`GET /v1/parcels/search`, `GET /v1/parcels/{id}` (ETag = version), `GET /v1/parcels/by-ulpin/{demo_ulpin}`, `GET /v1/parcels/near`, `GET /v1/parcels/{id}/title-chain`, `GET /v1/parcels/{id}/flags`, `POST /v1/parcels/bulk-lookup` (CSV ≤ 200), `POST /v1/ask` (SSE), `POST /v1/law/search`, `POST /v1/reports/title-draft` (PDF), `GET /v1/glossary`, `GET /v1/coverage`, `GET /tiles/parcels/{z}/{x}/{y}.mvt`, `/mcp`, `POST /v1/demo/login`, `GET /healthz`, `GET /healthz/db`, plus v2: `POST /v1/parcels/{id}/passports`, `GET /v1/passports/{id}`, `POST /v1/passports/verify`, `GET /status/{list_id}`, `GET /.well-known/did.json`, `GET /v/{id}/events` (SSE), `POST|DELETE /v1/passports/{id}/shares`, `POST|GET /v1/passports/{id}/subscriptions`, `POST /v1/admin/events`. All responses include an `X-Coverage` header. Errors use type URIs `https://titlivo.dev/errors/<slug>`.

## 11. Frontend

Routes: `/`, `/p/:parcelId`, `/compare`, `/law`, `/glossary`, `/bulk`, `/developers`, `/admin`, `/login`, `/signup`, `/mfa`, **`/v/:passportId`**, **`/verify`**, **`/lender`**.
- **Passport card** (dossier → *Issue Title Passport*): logo, parcel identity, status pill (LIVE mint / SUSPENDED saffron + reason / REVOKED red / EXPIRED grey, always icon + word), checks summary, valid-until, QR, *Share with lender*, *Download .jwt*.
- **Public verifier `/v/:passportId`** (mobile-first, no login): big status, "Signature valid — issued by did:web:…", checks list, coverage, disclaimer, "status checked N s ago", live updates via SSE; `/verify` accepts a dropped `.jwt`.
- **PWA (spec 7.6a):** `vite-plugin-pwa` with the manifest and 192/512 icons from `brand/`, `display: standalone`, app-shell precache only (never cache API, `/status/*` or `/v/*/events`); design every passport screen at 390 px first. No React Native, Capacitor or app-store build.
- **Lender inbox `/lender`:** shared passports with live status, grant expiry, webhook delivery log, open dossier while the grant is valid.
- **Admin inject-event panel:** presets (double sale F11, heir transfer F12, new charge, release) for the live-revocation demo.
- **Home:** one search box (any script; `/` focuses it), map, example queries, "Tour: one parcel, three audiences".
- **Dossier:** map left; right panel with identity, flag count and coverage; **ownership timeline ribbon**; flag cards with source chips (open the native record with the field highlighted and the canonical mapping); glossary term chips; **Show API call** panel (curl + JSON); Title draft button; Ask drawer.
- **Ask drawer:** streams tokens; record chips (blue) and law chips (purple); coverage footer; follow-ups; "Why this answer?" (tools called).
- **Map:** MapLibre + OpenFreeMap; MVT source `/tiles/parcels/{z}/{x}/{y}.mvt`; fill colour by `max_severity` with a patterned high-severity fill; village outlines at z ≤ 12; attribution control including OSM, OpenFreeMap and datameet ODbL; **list view alternative**.
- **Bulk:** CSV upload, results table, download.
- **Developers:** keys (shown once), scopes, quickstart, MCP guide, usage chart.
- **Admin** (`platform_admin`, aal2): usage, LLM spend, grounding-failure review, coverage, ingest issues, users, Grafana link.
- shadcn/ui only; WCAG 2.2 AA; `lang` attributes on native values.

## 12. Auth, security and data

- Supabase Auth: email+password (≥ 12) and Google; TOTP required for `platform_admin`.
- `supabase/shared/auth_hook.sql` is **identical across the three portfolio repos**: `public.app_memberships(user_id, app, org_id, role, scope jsonb)` + `public.custom_access_token_hook` → `claims.app_roles[app] = {org_id, role} || scope`; idempotent; grants to `supabase_auth_admin` only.
- RLS on all tables; `anon` reads only `titlivo.v_parcel_public` (masked via `titlivo.mask_name()`).
- Keys: scopes `parcels:read`, `parcels:pii`, `ask`, `bulk`, `mcp`; hashed; last-used; revocable.
- Query log stores the question hash, language, tools, tokens and latency; never the raw question for anon; no user IDs sent to Gemini.
- Sign-up shows a plain-language privacy notice; consent recorded.

## 13. Observability

Spans: `agent.run`, `agent.tool.<name>`, `llm.generate` (GenAI attributes: model, input/output tokens), `kb.search`, `grounding.check`, `mcp.call`, `tiles.render`. Metrics: `titlivo_llm_tokens_total`, `titlivo_llm_cost_usd_total`, `titlivo_grounding_failures_total`, `titlivo_ask_latency_seconds`, `titlivo_mcp_calls_total`, `titlivo_tile_latency_seconds`, `titlivo_rate_limited_total`. Provision `infra/grafana/titlivo.json` with alerts per spec 10.2.

## 14. Infrastructure and production deployment

- **Local:** `docker-compose.dev.yml` runs `grafana/otel-lgtm`; Supabase via the CLI; `Dockerfile.local` (API + built web) for the offline laptop demo.
- **`infra/Dockerfile.api`** (production API only, no web): `python:3.12-slim`, Pango libs (WeasyPrint), `uv sync --frozen --no-dev`, non-root user, `EXPOSE 8000`, `CMD ["uvicorn","titlivo.main:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips","*"]`, `HEALTHCHECK` on `/healthz`. Handle SIGTERM gracefully (finish in-flight requests, stop the dispatcher).
- **Backend: Amazon ECS Express Mode (ap-south-1):** created once with `aws ecs create-express-gateway-service` (spec 15.2, step 2): port 8000, health `/healthz`, `--cpu 512 --memory 1024`, `--scaling-target minTaskCount=1,maxTaskCount=3,autoScalingMetric=REQUEST_COUNT_PER_TARGET,autoScalingTargetValue=200`, env + `secrets` from Secrets Manager (`titlivo/prod/*`). Deploys use `aws ecs update-express-gateway-service --service-arn … --primary-container '{"image":"…"}'`. Load-balancer idle timeout 300 s (SSE/MCP).
- **Frontend: AWS Amplify Hosting:** `amplify.yml` (appRoot `web`, pnpm, `dist`), SPA rewrite to `/index.html`, `customHttp.yml` with HSTS, nosniff, Referrer-Policy and a CSP allowing the API host, Supabase, `tiles.openfreemap.org`. Env: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_MAP_STYLE`.
- **Database:** Supabase **Pro**, ap-south-1; `scripts/migrate_cloud.sh` (extensions, shared auth hook, migrations tracked in `titlivo.applied_migrations`); connect through the **transaction pooler (6543)** with psycopg `prepare_threshold=None`.
- **CI/CD:** `ci.yml` (lint, types, tests, defect recall, crypto vectors, e2e with `LLM_MODE=mock`); `deploy.yml` on push to `main` → GitHub OIDC `aws-actions/configure-aws-credentials@v4` → `amazon-ecr-login@v2` → build/push `titlivo-api:<sha7>` → `update-express-gateway-service` → `aws ecs wait services-stable` → smoke `curl /healthz` and `/.well-known/did.json`. Amplify builds the frontend on push. IAM JSON lives in `infra/aws/` (deploy role trust limited to `repo:<owner>/titlivo:ref:refs/heads/main`).
- **Brand:** copy `brand/` assets into `web/public` per `brand/BRAND.md`; `index.html` sets the favicon, apple-touch-icon, `og:image`, `theme-color #0B1736`; `manifest.webmanifest` uses the 192/512 icons.

## 15. Milestones (one PR each; stop and summarise after each)

| # | Milestone | Done when |
|---|---|---|
| M0 | Scaffold, Makefile (`dev`, `test`, `demo`, `lgd-load`, `villages`, `synth`, `ingest`, `kb-download`, `kb-ingest`), CI, `/healthz` | CI green |
| M1 | Migrations (extensions, schemas, tables, indexes), LGD + village polygon loaders, synthetic generator with planted defects | 18 villages, ~2,000 parcels generated reproducibly |
| M2 | Units, transliteration, glossary, adapters (3 states), harmonise + ingest validation | adapter golden tests pass |
| M3 | Title-chain SQL + flags F01–F10 + `check_defects` gate + `sql/demo/*.sql` | recall 100 %, precision ≥ 98 % |
| M4 | Auth (JWT/JWKS, keys, scopes), masking view, REST parcels endpoints, coverage header, problem+json | masking tests for anon/citizen/key pass |
| M5 | MVT tiles endpoint + caching | p95 < 150 ms locally |
| M6 | Web: home, search, map, dossier (timeline, flags, chips, Show API call), glossary page | Playwright: search → dossier |
| M7 | KB download + Docling ingest on the RTX 3060 + hybrid search + `/v1/law/search` | RAG promptfoo ≥ 90 % section hit |
| M8 | Agent + grounding validator + template fallback + SSE + answer cache + `LLM_MODE=mock` | agent promptfoo ≥ 97 % grounded |
| M9 | FastMCP server mounted at `/mcp` + auth middleware + parity tests + `docs/mcp.md` | Inspector calls all 6 tools |
| M10 | Title draft PDF + bulk lookup + `/bulk` page | PDF renders; 200-row CSV < 10 s |
| M11 | Red-team suite, admin console, telemetry + Grafana dashboard, model card, security FAQ | 0 red-team failures |
| M13 | **Title Passport**: DID document, signing, status lists, Python + TS verifiers with shared vectors, QR, `/v/:id` verifier page, passport card in the dossier | vectors pass in both languages; a tampered JWT fails |
| M14 | **Sentinel F11–F16 + monitoring + outbox + share grants + subscriptions + lender inbox + admin inject-event panel** | Playwright two-page test: inject F12 → verifier shows SUSPENDED ≤ 5 s; outbox exactly-once tests pass |
| M15 | **AWS production deploy**: `Dockerfile.api`, ECR, ECS Express service, Secrets Manager, Supabase Pro migration, Amplify + `amplify.yml` + `customHttp.yml`, OIDC `deploy.yml`, budget and 5xx alarms | public frontend + API URLs pass the go-live checklist (spec 15.3) |
| M12 | README (logo header, live links, video), quickstart, lender guide, passport verification guide, MCP guide, **public Postman workspace** (collection + local/prod environments + tests), **3 Jupyter notebooks** (`notebooks/`, run against the live API), tour | done after M15 |
| M16 | **Demo media, complete coverage** (spec 16.5, 16.7): create `docs/demo-coverage.yaml` with C01–C65 exactly as spec 16.7 (id, text, spec ref, screenshot files, chapter, film act). Playwright projects `demo-desktop` (1440×900) and `demo-mobile` (390×844, DPR 2); `web/e2e/demo/flows/NN-*.spec.ts`, one per flow 01–19, each step tagged with its C-IDs and writing `manifest.json` (titles, captions, `boundingBox` highlights); one planted parcel per flag F01–F16; non-web captures via `ansi-to-html` terminal cards, `pdftoppm` PDF pages, `jupyter nbconvert --execute` notebooks, `newman` + htmlextra report, MCP Inspector UI, Mailpit UI, Grafana UI, and the live URLs for flow 19. `walkthrough.spec.ts` records with `page.screencast` at 1920×1080, `showChapter` per flow (19 chapters), `showActions`, injected cursor dot, two contexts for live revocation, plus one clip per flow. Scripts `demo:shots`, `demo:record`, `demo:mp4` (ffmpeg H.264 `-preset veryfast -crf 20 -pix_fmt yuv420p -movflags +faststart`), `demo:chapters`, `demo:verify` (writes `coverage-report.md`, exits non-zero unless every C-item has screenshot ✓, chapter ✓, film act ✓; checks screenshots are non-blank) | `demo:verify` reports **65/65** for screenshots and chapters; two runs give identical screenshots; MP4s play in Windows |
| M17 | **Cinematic story film, long-form** (spec 16.6): `gen_backgrounds.py` (ComfyUI HTTP API, SDXL 1.0 base, 1152×640, 15 scenes from `prompts.yaml`, fixed seeds, negative prompt bans people/text/logos, Real-ESRGAN ×2); `voice/script.yaml` covering every C-item across Acts I–VIII; `tts.py` (Indic Parler-TTS fp16 on CUDA; speakers Mary narrator, Sunita/Swapna Kavya, Sanjay Ramesh-kaka, Thoma Mr Iyer, Divya/Meera Neha, Dinesh Arjun; ffmpeg loudnorm −16 LUFS); `peeps.ts` (Open Peeps CC0 → six characters incl. silhouette); Remotion `TitlivoStory`: one component per act, scene durations from audio via `calculateMetadata`, each scene exports its C-IDs, lip movement from `visualizeAudio`, film look (2.39:1 letterbox, grain, vignette, light leaks, grade, act title cards), journey graphics (device frames playing the real recordings, manifest highlight boxes, India-map path, LIVE→SUSPENDED shockwave, webhook particle, terminal glow), burned-in English subtitles, disclosure end card; `demo:story` (`--concurrency=4`), `demo:story-chapters` | ≈ 11–14 min MP4 renders on the laptop; voice and picture in sync; `demo:verify` reports **65/65** including film acts; no people/text/logos in backgrounds; numbers only from `metrics.json` |

## 16. Testing requirements

- Units/transliteration: Hypothesis round trips; cross-script search finds the same party.
- Adapter golden files: 20 per state.
- SQL: crafted chains (clean, break, partition, inheritance, mortgage → release).
- Masking: one parametrised test over REST, MCP and agent tools for anon, citizen and key-without-pii.
- MCP: FastMCP in-memory client; tool list and schemas snapshot; 401 without a key.
- Agent: mock-mode unit tests; promptfoo suites in `evals/promptfoo/` (RAG, agent, red team with injection strings in `other_rights`).
- E2E: Playwright tour flow with `LLM_MODE=mock`.
- Perf smoke: Locust on search, dossier and tiles.

## 17. Coding conventions

ruff (100 cols), mypy strict, async handlers with a psycopg async pool, SQL in files with named params, Pydantic models for every request/response/tool result. TS strict; API types generated with `openapi-typescript`. Conventional Commits. Update `docs/quickstart.md` and `docs/mcp.md` when contracts change.

## 18. Do NOT

- Do not let the LLM produce facts that are not in tool output, or say "safe", "clear title", "legal opinion" or "guaranteed".
- Do not return unmasked names to anon callers through any surface.
- Do not add OCR, Celery/Redis, an ORM, Next.js, a local LLM or a paid map provider.
- Do not copy the GoRT or acts wholesale into the UI; quote short passages with citations.
- Do not use real people's names, real survey records or government logos.
- Do not use `supabase db push` against the cloud project; use `scripts/migrate_cloud.sh`.
- Do not ship demo media with any coverage item missing (`demo:verify` must report 65/65), and when a feature is added, add its C-item first.
- Do not hand-edit screenshots or invent metrics in the video; capture from the running app with `LLM_MODE=mock`, a fixed clock and seed data, keep the "Synthetic data" ribbon visible. Voice only from `voice/script.yaml` via Indic Parler-TTS; no music; no real people's likeness or voices; backgrounds without people, text or logos; disclosure end card always present.
- Do not add a payment gateway, Kubernetes, Terraform, Rust/gRPC services, Jenkins, Datadog, Firecrawl, Kafka, Selenium, Prisma, Elasticsearch or Neon (spec Annexure D).
- Do not deploy to Railway, App Runner or a single VM; production is ECS Express Mode + Amplify (spec 15.2).
- Do not put names, phone numbers or raw evidence inside a passport, or describe it as a guarantee, title certificate or legal digital signature.
- Do not implement your own JWS/EdDSA or gzip/bitstring encoding outside `status_list.py`; do not query the database during passport verification.

## 19. When unsure

Follow the specification; if it is silent, choose the simplest option that keeps rules 1–10, record an ADR in `docs/adr/`, and mention it in the PR.
