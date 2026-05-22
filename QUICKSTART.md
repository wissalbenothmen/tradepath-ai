# Quickstart

Local setup in 10 minutes on Windows, macOS, or Linux.

## 0. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 – 3.13 | `python --version` |
| Node | 20 LTS or newer | `node --version` |
| Git | any | for cloning |

You do **not** need PostgreSQL, Redis, or any AI API keys to run the demo —
the app falls back to SQLite + deterministic AI fixtures by default.

## 1. Clone

```bash
git clone https://github.com/your-org/tradepath-ai.git
cd tradepath-ai
```

## 2. Backend

### 2a. Virtualenv + deps

```bash
cd backend
python -m venv .venv
```

Activate it:

| OS | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Windows (Git Bash) | `source .venv/Scripts/activate` |
| macOS / Linux | `source .venv/bin/activate` |

```bash
pip install -r requirements.txt
```

### 2b. .env

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

The defaults already work for the demo (`SQLite` DB, `MOCK_WHISPER=true`).
Edit `.env` if you want to wire a real OpenAI / DeepInfra / Azure key.

> **`SECRET_KEY` matters.** The validator rejects anything shorter than 32
> characters or matching known weak defaults. The committed `.env` has a
> safe dev value; rotate it before any non-local deployment.

### 2c. Seed the demo tenant

```bash
python -m scripts.seed_demo
```

Output:

```
Acme Trade Co  -> {'shipments': 32, 'classifications': 95, 'screenings': 64,
                   'declarations': 31, 'coos': 13, 'ftas': 50, 'documents': 34,
                   'amendments': 2}
NorthStar      -> {'shipments': 7,  ...}
```

The script is **idempotent** — re-run it to reset back to a known state. It
creates two tenants (Acme + NorthStar) so you can visually demonstrate
tenant isolation.

### 2d. Run the API

```bash
uvicorn app.main:app --reload --port 8007
```

Verify:

```bash
curl http://127.0.0.1:8007/health
# {"status":"ok","app":"TradePath AI","version":"1.0.0"}

curl http://127.0.0.1:8007/readyz
# {"status":"ready","checks":{"database":"ok"}}
```

Swagger UI: **http://localhost:8007/api/docs**

## 3. Frontend

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5007**.

The Vite config proxies `/api` → `http://127.0.0.1:8007`, so no CORS dance is
needed in dev.

## 4. Sign in

| Email | Password | Role | Tenant |
|---|---|---|---|
| `demo@tradepath.ai` | `DemoPass1!` | Admin | Acme |
| `broker@tradepath.ai` | `BrokerPass1!` | Customs Broker | Acme |
| `compliance@tradepath.ai` | `CompliancePass1!` | Trade Compliance | Acme |
| `otherco@tradepath.ai` | `OtherCoPass1!` | Admin | **NorthStar** (different tenant) |

The login page has a "Try the demo tenant" helper that fills the form for you.

## 5. What to click first

| Goal | Page | Why |
|---|---|---|
| Get the elevator-pitch view | `/dashboard` | $2.3M savings hero, streaming AI insights, action queue |
| See compliance volume | `/analytics` | 6 months of trend + FTA savings + jurisdictions |
| Drill into a shipment | `/shipments` then click a row | AI summary, voice ↔ docs cross-validation |
| Try the keyboard | Anywhere — press **⌘K / Ctrl+K** | Command palette with AI shortcuts |
| Prove isolation | Sign in as `otherco@tradepath.ai` | 7 shipments, none of Acme's data visible |

## 6. Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest        # Windows
# or: python -m pytest                    # if venv is active
```

You should see `79 passed`.

For the frontend:

```bash
cd frontend
npx tsc --noEmit          # type-check (no build artifacts)
```

## 7. Common gotchas

- **Backend port is 8007**, frontend port is 5007. Both are set in
  `backend/.env.example` and `frontend/vite.config.ts`.
- **Database is SQLite by default** (`tradepath.db` next to `app/`). To use
  Postgres, set `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db`
  in `.env` and re-run `python -m scripts.seed_demo`.
- **AI keys are optional**. Without them, every AI service falls back to
  deterministic fixtures.
- **`SECRET_KEY` validator**: ≥32 chars, must not be a known weak default
  (rejects `change-me-in-production`, etc.). Set a real value in your `.env`.

## 8. Next steps

- [ARCHITECTURE.md](ARCHITECTURE.md) — how the pieces fit together.
- [DEPLOYMENT.md](DEPLOYMENT.md) — running this in a real environment.
- [CONTRIBUTING.md](CONTRIBUTING.md) — sending your first PR.
