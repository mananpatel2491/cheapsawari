# Quickstart: Cloud Platform & Ops

## 1. See structured logging locally (no cloud needed)

Run the API (spec 001 quickstart) and watch the console: compact
`LEVEL  cheapsawari.<domain>  event  k=v` lines. Set `LOG_LEVEL=DEBUG` in `.env` for
more. To preview the Cloud Run JSON shape:

```bash
python - <<'PY'
import os; os.environ["K_SERVICE"] = "x"     # BEFORE importing obs
from src import obs
obs.configure_logging()
obs.event(obs.get_logger("demo"), "poll.run", polled=3, recorded=2)
PY
```

## 2. Terraform: validate/plan against live GCP (read-only until apply)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars     # set poll_token (gitignored)
terraform init && terraform fmt -check && terraform validate
terraform plan        # empty state → reports 11 to create; run import.sh to adopt
bash import.sh        # once; afterwards plan should show no changes
```

## 3. Deploy / operate (owner commands, from docs/DEPLOYMENT.md)

```bash
# redeploy the app (merges env, preserving secrets)
gcloud run deploy cheapsawari-api --source . --region us-central1 \
  --allow-unauthenticated --project cheapsawari

# flip an env var without a build
gcloud run services update cheapsawari-api --region us-central1 \
  --project cheapsawari --update-env-vars "KEY=VALUE"

# hosting (friendly URL)
firebase deploy --only hosting
```

## 4. Production queries (Logs Explorer / gcloud)

```bash
# did the poll run today?
gcloud logging read 'resource.labels.service_name="cheapsawari-api" AND jsonPayload.event="poll.run"' --limit 3

# failed sign-ins (see docs/LOGGING.md for the full catalog)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="cheapsawari-api" AND jsonPayload.event="auth.login" AND jsonPayload.outcome="denied"' --limit 10
```

Live smoke: `curl https://cheapsawari.web.app/health` and the same on
`https://cheapsawari-api-444653658968.us-central1.run.app/health` — both hit the one
service.
