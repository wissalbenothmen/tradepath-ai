# Deployment

> **Status.** This document describes a **manual** deploy path. A Dockerfile
> + docker-compose + Helm chart are on the roadmap (see `CHANGELOG.md`
> "Roadmap" section). The previous version of this doc referenced a
> `docker-compose.yml` that did not exist — that has been removed.

## 1. Target architecture (minimum viable)

```
            Cloudflare / CloudFront / Azure Front Door
                          │ HTTPS + WAF
                          ▼
        ┌────────────────────────────────────────┐
        │   Static SPA (S3 / Blob + CDN)         │  ← built from frontend/
        └────────────────────────────────────────┘
                          │ /api → reverse proxy
                          ▼
        ┌────────────────────────────────────────┐
        │   FastAPI (gunicorn + UvicornWorker)   │  ← built from backend/
        │   2+ replicas behind a load balancer   │
        └─────────────┬──────────────────────────┘
                      │ SSL (sslmode=require)
                      ▼
        ┌────────────────────────────────────────┐
        │   PostgreSQL 16 (managed)              │
        └────────────────────────────────────────┘
```

## 2. Backend

### 2a. Install

```bash
python -m venv /opt/tradepath/.venv
/opt/tradepath/.venv/bin/pip install -r requirements.txt
```

### 2b. Environment

Copy `.env.example` to `.env` (or use your secret store) and set:

| Variable | Required | Example |
|---|---|---|
| `SECRET_KEY` | **yes** | 64-char hex from `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | **yes** | `postgresql+asyncpg://user:pass@db.host:5432/tradepath?sslmode=require` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `480` (8 hours; default) |
| `ALLOWED_ORIGINS` | yes (prod) | `["https://app.tradepath.ai"]` |
| `RATE_LIMIT_PER_MINUTE` | no | `60` |
| `OPENAI_API_KEY` | optional | enables live HS / FTA / declaration AI |
| `OPENAI_MODEL` | no | `gpt-4.1-mini` |
| `DEEPINFRA_API_KEY` | optional | enables live Whisper voice amendments |
| `MOCK_WHISPER` | no | `false` in prod |
| `AZURE_DI_ENDPOINT` | optional | enables live document OCR |
| `AZURE_DI_KEY` | optional | — |
| `AZURE_STORAGE_CONNECTION_STRING` | optional | — |
| `AZURE_STORAGE_CONTAINER` | no | `trade-docs` |
| `REDIS_URL` | optional | unused today; reserved for the Arq worker roadmap item |
| `SDN_REFRESH_HOURS` | no | `4` |
| `DEBUG` | no | **must be `false` in prod** — toggles rate-limit bypass |
| `SQL_ECHO` | no | `false` (Decouple from DEBUG; only enable for local SQL debugging) |

### 2c. Initialise the schema

Today this is `Base.metadata.create_all` on app startup (see roadmap to move
to Alembic). The migration file `backend/migrations/V001__init_schema.sql`
is the Postgres baseline if you prefer to run it manually:

```bash
psql "$DATABASE_URL" -f backend/migrations/V001__init_schema.sql
```

### 2d. Run with gunicorn

```bash
/opt/tradepath/.venv/bin/gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 4 \
    --bind 0.0.0.0:8007 \
    --timeout 60 \
    --graceful-timeout 30 \
    --access-logfile - \
    app.main:app
```

Use a systemd unit / nomad job / k8s Deployment for supervision.

### 2e. Health probes

| Endpoint | Use as |
|---|---|
| `GET /health` | k8s liveness — process up |
| `GET /readyz` | k8s readiness — DB reachable (returns 503 if not) |

## 3. Frontend

### 3a. Build the SPA

```bash
cd frontend
npm ci
npm run build
# dist/  is your static bundle
```

### 3b. Serve it

Upload `dist/` to any static host (S3 + CloudFront, Azure Blob + Front Door,
Netlify, Vercel, or a plain nginx). The bundle assumes the API is reachable
at the same origin under `/api/v1`. The simplest setup is to terminate TLS
at a CDN / reverse proxy that:

- serves `/*` from the static bundle, and
- proxies `/api/*` to the gunicorn workers.

## 4. Secrets & rotation

- Generate a new `SECRET_KEY` per environment (`python -c "import secrets; print(secrets.token_hex(32))"`).
- Rotate it on a quarterly schedule. All issued JWTs become invalid on
  rotation — plan for the user re-login.
- Never commit `.env`. The committed `.env.example` contains only
  placeholder / development values.

## 5. Backup & retention

| Asset | Recommended retention |
|---|---|
| Postgres point-in-time backup | 30 days |
| `audit_logs` table | 7 years (customs / SOX baseline) |
| Trade document blobs (S3/Azure) | 7 years, S3 Object Lock |

## 6. Production checklist

- [ ] `DEBUG=false` and `SQL_ECHO=false` in the prod env.
- [ ] `SECRET_KEY` rotated, ≥32 chars, stored in a secret manager.
- [ ] `ALLOWED_ORIGINS` lists only your real frontend origin(s).
- [ ] HTTPS terminated at the edge with HSTS.
- [ ] Postgres connection uses SSL (`sslmode=require` or stricter).
- [ ] Health + readiness probes wired into the orchestrator.
- [ ] `pytest` runs as a CI gate before deploy.
- [ ] OpenAI / DeepInfra / Azure DI keys provisioned (or deliberately
      omitted; the offline fallback will engage).
- [ ] Backup schedule verified.
- [ ] Sentry / Loki / Datadog log destination configured.

## 7. Rollback

The deploy is stateless. Roll back by switching the orchestrator to the
previous image tag. Database migrations today are non-destructive
(`create_all` only adds tables); when Alembic lands, rollback will require
explicit `alembic downgrade -1`.
