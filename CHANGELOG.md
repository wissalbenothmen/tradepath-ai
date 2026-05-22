# Changelog

All notable changes to TradePath AI are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Roadmap (planned)
- Alembic migrations; drop `Base.metadata.create_all` from the startup hook.
- LiteLLM-style gateway: timeouts, retries, prompt-versioning, cost ledger.
- pgvector for HS-code semantic search + nightly OFAC/BIS feed.
- Arq workers for Whisper / OCR / PDF (move off the request thread).
- Vitest + Playwright frontend test suite.
- Dockerfile + docker-compose + Helm chart.
- OpenTelemetry traces + Sentry + Prometheus metrics.

## [1.1.0] — 2026-05-20

### Added
- **Tenant isolation as a first-class concern.** Every domain table now
  carries a `company_id` column. Every router filters reads + mutations by
  `current_user.company_id`. Shared helpers in `app/tenant.py`.
  *(Closes audit findings: classification, screening, declaration, COO,
  FTA, documents, analytics cross-tenant leaks.)*
- **`/auth/invite`** — authenticated members can add a new user into their
  own tenant. Replaces the deprecated practice of accepting `company_id`
  from `/auth/register`.
- **`/readyz`** — Kubernetes-style readiness probe that verifies the DB is
  reachable. Returns 503 when degraded.
- **Five new analytics endpoints**: `/analytics/trends`,
  `/analytics/by-jurisdiction`, `/analytics/top-ftas`,
  `/analytics/action-queue`, `/analytics/ai-insights`. All tenant-scoped.
- **Password policy** — Pydantic validator enforces ≥8 chars + upper +
  lower + digit + symbol on `/auth/register` and `/auth/invite`.
- **Per-IP rate-limit** on `/auth/login` and `/auth/register`
  (10 / minute / IP), bypassed when `DEBUG=true` for local dev/tests.
- **Security headers middleware** — `X-Content-Type-Options`,
  `Strict-Transport-Security`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`, etc.
- **`SQL_ECHO` env var** — decouples SQLAlchemy echo from `DEBUG`.
- **Demo seed script** (`backend/scripts/seed_demo.py`) — 32 + 7 shipments
  across two tenants, 6 months of compliance history, ~250 rows of
  realistic AI artefacts (classifications, screenings, declarations, CoOs,
  FTA analyses, OCR documents, Whisper voice amendments).
- **11 security regression tests** covering all the above
  (`tests/test_security_tenant_isolation.py`).
- **Frontend AI showcase components**: `AISummaryCard`, `StreamingText`,
  `ConfidenceBar`, `Sparkline`, `KpiCard`, `StatusPill`, `MicButton`,
  `CommandPalette`, `EmptyState`, `ErrorBoundary`.
- **Design system overhaul** — dual-tone brand gradient (navy → blue →
  cyan), AI accent palette (purple → cyan), Inter + JetBrains Mono fonts,
  tabular numerals, dark-mode classes, semantic shadows, motion tokens.
- **Cmd+K command palette** with Navigate / AI / Action groups.
- **Rebuilt Dashboard** — $2.3M savings hero, compliance risk gauge,
  streaming AI insights, action queue, jurisdiction breakdown, sparklines.
- **Rebuilt Analytics** — 6-month volume + FTA savings area chart, FTA
  gradient bars, pipeline rail, sanctions pie, top destinations.
- **Rebuilt Shipments table** — search + status filter chips + StatusPill
  rows + responsive density.
- **Rebuilt ShipmentDetail** — AI summary card with streaming text, voice
  ↔ documents cross-validation panel wired to the real backend, voice
  transcript viewer, removed all hardcoded mock fixtures.
- **`LICENSE`** (MIT), **`SECURITY.md`** (threat model + disclosure),
  **`.editorconfig`**, **`.github/` PR + issue templates**.

### Changed
- `/auth/register` no longer accepts a client-supplied `company_id`.
- `get_current_user` now returns 401 (not 500) on a malformed UUID in the
  JWT `sub` claim.
- Frontend `tailwind.config.js` rebuilt around real design tokens. The dead
  `brand` palette is now actually consumed.
- `Toast` errors no longer surface "Invalid email or password" for every
  error — login now distinguishes 401, 429, network failures.
- `index.html` now ships a proper meta description, theme-color, gradient
  SVG favicon, Open Graph + Twitter cards, and Inter / JetBrains Mono
  preconnect.

### Fixed
- **Self-registration tenant-escalation vector** — closed.
- **Cross-tenant data leaks** on classifications, declarations, COOs, FTAs,
  documents, screenings, voice amendments — closed.
- **Cross-tenant analytics counts** (`/analytics/dashboard`) — scoped.
- **`localStorage` cache leak across users on logout** — `queryClient.clear()`
  now runs on auth failure + explicit logout.
- **Demo theatre in `ShipmentDetailPage`** (hardcoded mock cross-validation
  matrix, fake `setTimeout` async stubs) — removed; replaced with real
  backend cross-validation calls.
- **Synthesised "monthly trend" data** in `AnalyticsPage` — replaced with
  real `/analytics/trends` endpoint backed by tenant data.
- **`ShipmentSelector` type drift** — single canonical `Shipment` type
  derived from one place.
- **Hardcoded port 8037** in docs (README, ARCHITECTURE, DEPLOYMENT,
  QUICKSTART) — corrected to **8007** (backend) and **5007** (frontend).
- **Referenced-but-missing `docker-compose.yml`** in DEPLOYMENT.md —
  acknowledged as roadmap, manual deploy documented.
- **Broken Python one-liner** in QUICKSTART step 5 — replaced with
  `python -m scripts.seed_demo`.
- **Missing `LICENSE`** despite the README claim — added.

### Removed
- 12 `server*.log` files committed at `backend/` (dev artefacts).
- 3 `frontend_walk*.log` files at the repo root.
- `backend/.uvicorn.log`.
- 21 older underscore-named screenshots + `.console.json` companions in
  `project-audit/screenshots/`.
- Empty placeholder directories: `frontend/src/lib/`, `frontend/src/types/`,
  `backend/app/workers/`.

### Moved
- `walkthrough.py`, `patch_shots.py` → `scripts/`.
- `take_screenshots_final.py` → `scripts/take_screenshots_v1.py`.
- `backend/probe_apis.py` → `backend/scripts/probe_apis.py`.
- `backend/tradepath_api_test.py` → `backend/scripts/api_smoketest.py`.
- Older dash-named screenshots → `project-audit/screenshots-v1/`
  (kept as historical record).
- Latest screenshots → `project-audit/screenshots-v2/`.

## [1.0.0] — 2026-05-16

Initial production-ready beta build. See `project-audit/reports/`
(formerly `project-audit/*.md`) for the audit reports that drove the
1.1.0 rewrite.
