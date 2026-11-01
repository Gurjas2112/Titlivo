#!/usr/bin/env bash
# Production deploy (spec v2.2 lowest-cost path): Supabase (Mumbai) + Lightsail container + Amplify.
#
#   AWS_PROFILE=titlivo ./scripts/deploy.sh [--skip-data] [--skip-image] [--skip-web]
#
# Needs: aws sso login --profile titlivo · Docker running · .env.prod with DATABASE_URL (git-ignored).
# Secrets live in SSM Parameter Store /titlivo/prod/*; nothing secret is printed or committed.
set -euo pipefail
export MSYS_NO_PATHCONV=1 AWS_PAGER="" AWS_REGION=ap-south-1 PYTHONUTF8=1
export AWS_PROFILE="${AWS_PROFILE:-titlivo}"
cd "$(dirname "$0")/.."

SERVICE=titlivo-api
APP_ID=d2md8dgohc7hhh
API_URL="https://titlivo-api.p7gtxt73pr9fe.ap-south-1.cs.amazonlightsail.com"
API_HOST="${API_URL#https://}"
WEB_URL="https://main.${APP_ID}.amplifyapp.com"
SKIP_DATA=0 SKIP_IMAGE=0 SKIP_WEB=0
for a in "$@"; do case $a in --skip-data) SKIP_DATA=1;; --skip-image) SKIP_IMAGE=1;; --skip-web) SKIP_WEB=1;; esac; done

ssm() { aws ssm get-parameter --name "/titlivo/prod/$1" --with-decryption --query Parameter.Value --output text; }
step() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

step "Identity"
aws sts get-caller-identity --query Arn --output text | grep -q AWSReservedSSO || { echo "Use the SSO profile (aws sso login --profile titlivo)"; exit 1; }

step "Database URL → SSM"
if [ -f .env.prod ]; then
  DBURL=$(grep -E '^DATABASE_URL=' .env.prod | cut -d= -f2- | sed "s/^['\"]//; s/['\"]$//")
  aws ssm put-parameter --name /titlivo/prod/DATABASE_URL --type SecureString --value "$DBURL" --overwrite >/dev/null
fi
DBURL=$(ssm DATABASE_URL)

if [ $SKIP_DATA = 0 ]; then
  step "Migrate + load synthetic data into the production database"
  [ -f data/synth/villages.json ] || uv run --directory api python -m titlivo.tools.synth --seed 42
  uv run --directory api python -m titlivo.tools.migrate --url "$DBURL"
  uv run --directory api python -m titlivo.tools.ingest --url "$DBURL" | tail -3
fi

if [ $SKIP_IMAGE = 0 ]; then
  step "Build + push API image"
  TAG=$(git rev-parse --short HEAD)
  docker build -q -f infra/Dockerfile.api -t "$SERVICE:$TAG" .
  PATH="$HOME/bin:$PATH" aws lightsail push-container-image --service-name $SERVICE --label api --image "$SERVICE:$TAG" | tail -1
fi
IMAGE=$(aws lightsail get-container-images --service-name $SERVICE --query "containerImages[0].image" --output text)

step "Deploy $IMAGE"
python - "$IMAGE" > "$TEMP/containers.json" <<PY
import json, sys
print(json.dumps({"api": {"image": sys.argv[1], "ports": {"8000": "HTTP"}, "environment": {
  "APP_ENV": "prod", "DATABASE_URL": """$DBURL""",
  "PUBLIC_API_BASE": "$API_URL", "PUBLIC_WEB_BASE": "$WEB_URL",
  "ISSUER_DID": "did:web:$API_HOST", "CORS_ORIGINS": "$WEB_URL,http://localhost:5173",
  "PASSPORT_SIGNING_JWK": """$(ssm PASSPORT_SIGNING_JWK)""",
  "DEMO_API_KEY": "$(ssm DEMO_API_KEY)", "ADMIN_API_KEY": "$(ssm ADMIN_API_KEY)",
  "LLM_MODE": "live"}}}))
PY
cat > "$TEMP/endpoint.json" <<JSON
{"containerName": "api", "containerPort": 8000,
 "healthCheck": {"path": "/healthz", "intervalSeconds": 10, "timeoutSeconds": 5, "healthyThreshold": 2, "unhealthyThreshold": 3, "successCodes": "200"}}
JSON
aws lightsail create-container-service-deployment --service-name $SERVICE \
  --containers "file://$(cygpath -w "$TEMP/containers.json" 2>/dev/null || echo "$TEMP/containers.json")" \
  --public-endpoint "file://$(cygpath -w "$TEMP/endpoint.json" 2>/dev/null || echo "$TEMP/endpoint.json")" \
  --query "containerService.nextDeployment.version" --output text
rm -f "$TEMP/containers.json"
for i in $(seq 1 60); do
  STATE=$(aws lightsail get-container-service-deployments --service-name $SERVICE --query "deployments[0].state" --output text)
  echo "  deployment: $STATE"; [ "$STATE" = ACTIVE ] && break; [ "$STATE" = FAILED ] && { echo "Deployment failed; see: aws lightsail get-container-log --service-name $SERVICE --container-name api"; exit 1; }
  sleep 15
done

if [ $SKIP_WEB = 0 ]; then
  step "Build + deploy web to Amplify"
  (cd web && VITE_API_URL="$API_URL" npx vite build --logLevel warn)
  ZIP="$TEMP/titlivo-web.zip"; rm -f "$ZIP"
  (cd web/dist && python -c "import shutil;shutil.make_archive(r'${ZIP%.zip}','zip','.')")
  read -r JOB URL < <(aws amplify create-deployment --app-id $APP_ID --branch-name main --query "[jobId,zipUploadUrl]" --output text)
  curl -sf -X PUT -H "Content-Type: application/zip" --upload-file "$ZIP" "$URL"
  aws amplify start-deployment --app-id $APP_ID --branch-name main --job-id "$JOB" --query "jobSummary.status" --output text
  for i in $(seq 1 40); do
    S=$(aws amplify get-job --app-id $APP_ID --branch-name main --job-id "$JOB" --query "job.summary.status" --output text)
    echo "  amplify: $S"; [ "$S" = SUCCEED ] && break; [ "$S" = FAILED ] && exit 1; sleep 6
  done
fi

step "Smoke tests"
curl -fsS "$API_URL/healthz" && echo
curl -fsS "$API_URL/healthz/db" && echo
curl -fsS "$API_URL/.well-known/did.json" | head -c 120 && echo
curl -fsS -o /dev/null -w "web %{http_code}\n" "$WEB_URL/"
echo -e "\nLive:  $WEB_URL\nAPI:   $API_URL/docs"
