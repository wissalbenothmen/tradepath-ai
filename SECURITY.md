# Security Policy

## Supported versions

We support the latest minor release on the `main` branch. Older releases do
not receive security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a vulnerability

Please report security issues to **security@tradepath.ai** (or open a
[private Security Advisory](https://github.com/your-org/tradepath-ai/security/advisories/new)
on GitHub). Do **not** open a public issue.

We aim to acknowledge a report within **2 business days** and to ship a patch
or mitigation within **14 days** for high-severity issues. Please include:

- A description of the issue and the affected endpoint / page / module.
- Steps to reproduce (ideally with curl/HTTP traces or a minimal script).
- The expected impact (confidentiality / integrity / availability).
- Whether you would like public credit in the changelog.

## Threat model (high level)

TradePath AI handles regulated trade-compliance data (HS classifications,
denied-party screenings, customs declarations). The product threat surface
is grouped into four buckets:

### 1. Authentication & authorisation
- Bearer JWT tokens (HS256), 8-hour expiry by default.
- Per-IP rate-limit on `/auth/login` and `/auth/register` (10 / minute).
- Password policy: min 8 chars, must include upper + lower + digit + symbol.
- Self-registration creates a fresh tenant; **client-supplied `company_id`
  is ignored**. Users join an existing tenant only through `/auth/invite`
  performed by an already-authenticated member of that tenant.

### 2. Tenant isolation
- Every domain row carries a `company_id` (a.k.a. `org_id`) column.
- Every router filters reads + mutations by `current_user.company_id`.
- Cross-tenant probes for shipments, classifications, screenings,
  declarations, COOs, FTAs, documents, and voice amendments all return
  404 — we never leak existence of rows in other tenants.
- See `backend/tests/test_security_tenant_isolation.py` for the 11
  regression tests enforcing this.

### 3. Input validation
- Pydantic v2 schemas on every endpoint.
- Audio uploads: extension allow-list (.wav .mp3 .m4a .mp4 .webm .ogg .flac).
- Document uploads: type / size limits enforced at the platform edge.
- HS-classifier user input is sanitized for prompt-injection patterns.

### 4. Observability
- Structured request-ID middleware on every response (`X-Request-ID`).
- `/health` (liveness) and `/readyz` (DB readiness) probes.
- Global exception handler hides stack traces from clients.

## Known gaps (tracked in the roadmap)

- `python-jose` 3.3.0 → migrate to `PyJWT` (CVE-2024-33664).
- `passlib` 1.7.4 → migrate to `argon2-cffi`.
- LLM gateway: timeouts, retries, prompt-versioning, cost ledger are not
  yet centralised.
- Sanctions screening currently uses a small mock list for offline demos;
  production deployments must wire the nightly OFAC/BIS feed before going
  live (`backend/app/services/denied_party_screening.py`).

## Compliance posture

The platform is designed for SOC 2 Type II readiness — every privileged
action is recorded in `audit_logs`, including the AI reasoning trail for
human-reviewable decisions. SOC 2 / ISO 27001 audits are part of the
roadmap.
