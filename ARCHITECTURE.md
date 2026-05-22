# Architecture

## 1. High-level

```
                       ┌──────────────────────┐
                       │   Browser (React 18) │
                       │   Vite dev :5007     │
                       └──────────┬───────────┘
                                  │ HTTPS / Bearer JWT
                                  ▼
                       ┌──────────────────────┐
                       │   FastAPI :8007      │
                       │   /api/v1/*          │  ←  /api/docs (Swagger)
                       │                      │      /api/redoc
                       │   middleware:        │      /health  /readyz
                       │   - request-ID       │
                       │   - security headers │
                       │   - rate-limit (auth)│
                       │   - tenant scope     │
                       └──────────┬───────────┘
                                  │ SQLAlchemy 2 async
              ┌───────────────────┼─────────────────────┐
              ▼                                         ▼
   ┌──────────────────────┐                  ┌──────────────────────┐
   │   PostgreSQL 16      │                  │   AI side-cars       │
   │   (or SQLite dev)    │                  │   - OpenAI GPT-4.1   │
   │                      │                  │   - DeepInfra Whisper│
   │   - shipments        │                  │   - Azure DI (OCR)   │
   │   - hs_classifications                  │                      │
   │   - dps_screenings   │                  └──────────────────────┘
   │   - declarations     │
   │   - coos             │                  (each call has an
   │   - fta_analyses     │                   offline fallback)
   │   - audit_logs       │
   └──────────────────────┘
```

## 2. URL prefix

**Every API endpoint lives under `/api/v1/...`** (mounted in `app/main.py`).
The Swagger UI itself is at `/api/docs` (no prefix), and `/health` + `/readyz`
are deliberately un-versioned.

## 3. Backend layout

```
backend/app/
  main.py            ← FastAPI factory, lifespan, middleware, exception handlers
  auth.py            ← password hashing, JWT encode/decode, get_current_user
  database.py        ← async SQLAlchemy engine + session-per-request
  config.py          ← Pydantic Settings, SECRET_KEY validator
  tenant.py          ← shared require_shipment / require_tenant_owned helpers

  routers/
    auth.py                ← /auth/{register,login,me,invite} + rate-limit
    shipments.py           ← /shipments  + voice-records + cross-validate + brief.pdf
    classification.py      ← /classification — HS code w/ GRI trace
    screening.py           ← /screening — OFAC/BIS/EU/UN match
    declarations.py        ← /declarations — CBP / EU SAD / UK / AES + EDI
    coo.py                 ← /coo — USMCA / EUR.1 / Form A
    fta.py                 ← /fta — duty saving per agreement
    documents.py           ← /documents — upload + Azure DI OCR
    restrictions.py        ← /restrictions/check — ITAR / EAR / quota
    analytics.py           ← /analytics/{dashboard,trends,by-jurisdiction,
                            top-ftas,action-queue,ai-insights}
    shipment_amendments.py ← /shipment-amendments — voice upload + list

  services/                ← AI services with deterministic fallbacks
    hs_classifier.py
    denied_party_screening.py
    customs_declaration_service.py
    coo_generator.py
    fta_analyzer.py
    duty_calculator.py
    document_ocr.py
    whisper_service.py
    trade_amendment_analyzer.py
    amendment_brief_pdf_service.py
    audit_log_service.py
    import_restrictions.py

  models/                  ← SQLAlchemy 2 declarative models
    user.py · shipment.py · shipment_line_item.py · product.py
    hs_classification.py · denied_party_screening.py · customs_declaration.py
    certificate_of_origin.py · trade_document.py · fta_analysis.py
    audit_log.py · shipment_amendment.py
```

## 4. Frontend layout

```
frontend/src/
  App.tsx            ← BrowserRouter + PrivateRoute + Routes
  main.tsx           ← QueryClient + ErrorBoundary + StrictMode
  api.ts             ← axios client + endpoint registry + qk factory + logout()
  index.css          ← Tailwind layers + design tokens

  pages/
    LoginPage.tsx
    DashboardPage.tsx          ← AI insights, sparklines, action queue
    ShipmentsPage.tsx          ← search + filter chips + StatusPill rows
    ShipmentDetailPage.tsx     ← AI summary, voice cross-validation, transcript
    ClassificationPage.tsx
    ScreeningPage.tsx
    DeclarationsPage.tsx
    COOPage.tsx
    FTAPage.tsx
    DocumentsPage.tsx
    AnalyticsPage.tsx          ← multi-series area chart, FTA gradient bars

  components/
    Layout.tsx               ← sidebar (Workflow / AI Compliance / Insights) + Cmd-K
    CommandPalette.tsx       ← Cmd+K — Navigate / AI / Action groups
    AISummaryCard.tsx        ← gradient surface, streaming text, regenerate
    AIThinking.tsx           ← shimmer dots
    StreamingText.tsx        ← token-by-token reveal
    ConfidenceBar.tsx        ← semantic gradient bar
    KpiCard.tsx              ← KPI with sparkline + delta
    Sparkline.tsx            ← inline SVG sparkline
    StatusPill.tsx           ← icon + label + tone (canonical status colours)
    MicButton.tsx            ← Whisper-powered MediaRecorder wrapper
    EmptyState.tsx
    ErrorBoundary.tsx
    Toast.tsx
    Skeleton.tsx
    Badge.tsx
```

## 5. AuthN / AuthZ

- **JWT (HS256)** with 8-hour expiry by default (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Password policy** enforced via Pydantic validator: ≥8 chars + upper +
  lower + digit + symbol.
- **Self-registration** creates a new tenant (`company_id = uuid.uuid4()`) —
  the request body **cannot** specify `company_id` (audit-flagged escalation
  vector is closed).
- **Tenant invitations** flow exclusively through `/auth/invite`, which
  requires an authenticated caller and reuses *their* tenant.
- **Rate limit** on `/auth/login` and `/auth/register`: 10 requests / minute
  / IP (bypassed when `DEBUG=true` for local dev + tests).

## 6. Tenant isolation

Every domain row carries a `company_id` column. Every router filters reads
and mutations by `current_user.company_id`. The pattern lives in
`backend/app/tenant.py`:

```python
async def require_shipment(db, shipment_id, user) -> Shipment:
    """Returns the Shipment iff user.company_id matches; else 404 (not 403)."""

async def require_tenant_owned(db, Model, obj_id, user):
    """Generic per-resource version of the above."""
```

11 regression tests in `tests/test_security_tenant_isolation.py` enforce
that:

1. `/auth/register` ignores any client-supplied `company_id`.
2. Weak passwords are rejected (422).
3. `/auth/invite` adds the invitee to the inviter's tenant.
4. Cross-tenant reads of shipments / classifications / declarations /
   screenings return 404.
5. `/analytics/dashboard` counts are scoped to the caller's tenant.
6. Malformed UUID in JWT `sub` returns 401, not 500.
7. `/readyz` reports database health.

## 7. AI pipeline

Every AI service uses the same shape:

```python
async def some_ai_call(...) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        return _deterministic_fallback(...)
    try:
        result = await _openai.chat.completions.create(model=..., ...)
        return _parse(result)
    except Exception:
        return _deterministic_fallback(...)
```

This is why **the demo works fully offline** — without an `OPENAI_API_KEY`
the seeded data still flows through the same code path, and every screen
renders. In production the fallback is the safety net for outages.

The `analytics` router additionally surfaces **AI insights** as deterministic
rules over tenant data (see `/analytics/ai-insights`). When the centralised
LLM gateway lands, these will be re-generated from a prompt template; the
contract stays the same.

## 8. Data model summary

```
users ──▶ company_id ────▶ shipments
                           ├─▶ shipment_line_items
                           ├─▶ hs_classifications
                           ├─▶ denied_party_screenings
                           ├─▶ customs_declarations
                           ├─▶ certificates_of_origin
                           ├─▶ fta_analyses
                           ├─▶ trade_documents
                           └─▶ shipment_amendments       (← Whisper transcripts)
audit_logs ─▶ user_id ─▶ shipment_id
```

The full data dictionary lives in `backend/app/models/` (SQLAlchemy
declarative) and `backend/migrations/V001__init_schema.sql` (Postgres
baseline).

## 9. Observability

| Probe | Path | Purpose |
|---|---|---|
| Liveness | `/health` | Process is up |
| Readiness | `/readyz` | Database is reachable (`SELECT 1`) |
| Tracing | `X-Request-ID` header | Echoed on every response, logged on every line |

The next observability ticket is to wire `structlog` + Sentry + Prometheus
+ OpenTelemetry traces.
