# Titlivo developer commands (Linux/macOS/WSL/Git Bash). See docs/runbooks/demo.md.
API = uv run --directory api
export PYTHONUTF8 = 1

.PHONY: db keys data synth ingest check test lint api web dev demo-media

db:            ## start local PostGIS (port 54329)
	docker compose -f infra/docker-compose.dev.yml up -d db

keys:          ## generate local passport signing key + demo API keys into .env
	$(API) python -m titlivo.tools.keys

synth:         ## synthetic villages, parcels, native records, planted defects
	$(API) python -m titlivo.tools.synth --seed 42

ingest:        ## migrations + adapters → canonical tables + flags
	$(API) python -m titlivo.tools.migrate
	$(API) python -m titlivo.tools.ingest

data: synth ingest check

check:         ## defect recall/precision gate (100 % / ≥ 98 %)
	$(API) python -m titlivo.tools.check_defects

test:
	$(API) pytest -q

lint:
	$(API) ruff check src tests
	cd web && npm run lint --if-present && npm run typecheck

api:
	$(API) uvicorn titlivo.main:app --reload --port 8000

web:
	cd web && npm run dev

demo-media:    ## screenshots + videos (app must be running)
	cd web && npm run demo:shots && npm run demo:record && npm run demo:mp4
