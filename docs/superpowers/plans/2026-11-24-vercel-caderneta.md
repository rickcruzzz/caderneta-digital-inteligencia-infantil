# Vercel Caderneta Digital Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Publish a fully working Caderneta Digital UI and HTTP integration API on one Vercel origin backed by a dedicated MongoDB Atlas database.

**Architecture:** Next.js provides the Vercel UI; Python FastAPI runs as Vercel serverless functions under `/api`. FastAPI is the only persistence layer and stores normalized projections/events in `caderneta_digital`. The Colab notebook remains a demo artifact and no Streamlit process is deployed to Vercel.

**Tech Stack:** Next.js, TypeScript, FastAPI, PyMongo, Pydantic, MongoDB Atlas, Vercel Functions.

**Spec:** `docs/superpowers/specs/2026-11-24-vercel-caderneta-design.md`

## Global Constraints
- Preserve SQL Server and all its data; do not connect to it directly.
- Never drop or modify `sample_mflix`; use only `caderneta_digital`.
- Do not commit credentials; use Vercel encrypted environment variables and ignored local env files.
- Use only synthetic demo data; do not represent absent events as confirmed non-performance.
- Keep the integration API idempotent and retain source event history/operator notes.
- Deploy only after unit tests, Next build, and API smoke tests pass.

## Review Focus
- Replayed/corrected event IDs do not duplicate records or erase operator notes (API integration tests).
- Missing triage differs from source-confirmed not-performed and unknown status (monitoring tests).
- Missing/wrong API key cannot read or change private app data (auth API tests).
- Empty Mongo renders a useful UI rather than failing (Next page smoke test).
- Vercel rewrites preserve `/api` route paths and Mongo failures do not expose credentials (deployment smoke tests).

---

### Task 1: Vercel and Mongo scaffolding

**Files:** `package.json`, `package-lock.json`, `vercel.json`, `.gitignore`, `api/`, `tests/`

**Interfaces:** Produces a Vercel project with Next.js at `/` and FastAPI behind `/api/*`; consumes environment variables from the design spec.

- [ ] Add failing smoke tests for `/api/health`, `/api/v1/integracao/registros`, required API key, and dedicated database name.
- [ ] Run tests and confirm expected failures.
- [ ] Add Vercel/Next/Python configuration; do not point at or overwrite the root SQL project.
- [ ] Run route smoke tests and Next build.

### Task 2: FastAPI Mongo services

**Files:** `api/index.py`, `api/database.py`, `api/models.py`, `api/services.py`, `api/monitoring.py`, `api/reports.py`, `tests/`

**Interfaces:** `get_db()`, `ensure_indexes(db)`, `process_event(db,event)`, `refresh_child_monitorings(db,source,child)`, and FastAPI routes for auth, dashboard, children, monitorings, summaries, reports, audit, health, and integration.

- [ ] Add tests for invalid auth, idempotency, corrections/notes, out-of-order events, triage states, and summaries.
- [ ] Verify tests fail before implementation.
- [ ] Implement Mongo-backed endpoints and session authentication; use an HttpOnly signed session cookie for UI and a separate `X-API-Key` for source integration.
- [ ] Run API test suite and verify no response/log includes credentials.

### Task 3: Next.js Caderneta Digital UI

**Files:** `app/`, `components/`, `lib/api.ts`, `tests/`

**Interfaces:** Same-origin fetches to FastAPI; pages for overview, intelligence/data quality, monitoring, child detail, discharge summary/PDF, integration, and audit.

- [ ] Add a failing empty-database page test and API auth flow test.
- [ ] Verify tests fail before UI implementation.
- [ ] Implement responsive UI, login/logout, metrics/charts/filters, monitor updates/history, and discharge-summary lifecycle.
- [ ] Run UI tests, typecheck, and production build.

### Task 4: Atlas setup and demo data

**Files:** `scripts/seed_demo.py`, `CONTRATO_INTEGRACAO.md`, `README.md`, notebook cells

**Interfaces:** Idempotent setup creates collections/indexes in `caderneta_digital`; inserts synthetic events only when absent.

- [ ] Test that setup leaves `sample_mflix` unchanged and never drops existing collections.
- [ ] Implement explicit collection/index setup and synthetic seed keyed by stable `event_id`.
- [ ] Run tests against Mongo mock; if Atlas credentials are valid, ping and seed only the dedicated database.

### Task 5: Vercel deployment

**Files:** Vercel project settings and repository metadata only; no secrets committed.

- [ ] Run the complete Python suite, UI tests, typecheck, and production build.
- [ ] Configure production/preview env vars through the authenticated Vercel CLI using local values without printing them.
- [ ] Deploy preview and verify `/api/health`, UI login, and one synthetic API event.
- [ ] Promote the verified deployment, push the source branch to GitHub, and report URLs/status without exposing secrets.