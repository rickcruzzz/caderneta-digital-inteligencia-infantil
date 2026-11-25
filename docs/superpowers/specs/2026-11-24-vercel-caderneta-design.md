# Caderneta Digital on Vercel

## Intent

Deploy the Caderneta Digital complementary application as one Vercel project. The Next.js interface and FastAPI integration endpoints share the same origin and MongoDB Atlas database. The existing SQL Server application remains untouched and continues to be the source of official records; this project accepts HTTP/JSON events and does not connect to SQL Server.

## Goals

- Serve the authenticated operational UI from Vercel using Next.js.
- Serve `/health` and versioned integration/read/write APIs from a Python FastAPI Vercel Function.
- Use one dedicated MongoDB database named `caderneta_digital`, leaving `sample_mflix` and all other databases unchanged.
- Keep event ingestion idempotent and preserve operator notes/history when source events are corrected.
- Show synthetic demo records only; actual source records arrive through the documented API contract.
- Keep secrets only in local ignored environment files and Vercel encrypted environment variables.

## Non-goals

- Do not delete, rename, or migrate the existing SQL Server database.
- Do not import SQL Server data directly; source-to-app integration is HTTP/JSON only.
- Do not deploy the long-running Streamlit process on Vercel. The existing Colab notebook remains a development/demo artifact; the hosted UI is Next.js because Vercel is serverless.
- Do not claim clinical diagnosis, validate unapproved clinical protocols, or use real patient records in demo data.

## Architecture

Vercel serves the Next.js app and routes `/api/*` to a Python FastAPI function. FastAPI owns MongoDB access, authentication, event intake, monitoring, summaries, and audit APIs. The Next.js UI calls the same-origin API; it never receives the MongoDB URI. The API uses a cached PyMongo client and a dedicated `caderneta_digital` database. `sample_mflix` is preserved.

Vercel environment variables: `MONGO_URI`, `MONGO_DATABASE`, `API_INTEGRATION_KEY`, `APP_ADMIN_USERNAME`, `APP_ADMIN_PASSWORD`, and `SESSION_SECRET`. Local `.env` files remain git-ignored. The integration key is separate from application login credentials.

## Data behavior

Only normalized fields required for the UI are projected to Mongo. Event records are retained with source IDs/version history. Repeated event IDs are idempotent; corrections merge supplied fields without deleting operator notes; older events do not replace newer projections. Missing triage events are labeled `SEM_INFORMACAO`, never `NAO_REALIZADO`. Rules requiring a time interval stay disabled until an administrator enters a locally approved threshold.

Initial Atlas setup creates collections/indexes in `caderneta_digital` and inserts only clearly synthetic demo events if that database is empty. It never drops collections or writes to `sample_mflix`.

## Verification

- Python tests cover invalid/missing API key, schema validation, event batch/lookup, idempotency, correction/notes, event ordering, monitoring states/history, temporal-rule configuration, and summary output.
- Next.js build and typecheck pass.
- A local smoke test verifies UI/API route wiring and empty-database behavior.
- After credentials are installed through the Vercel CLI, production health, login, and one synthetic event are checked without printing secrets.

## Rollout

Create a feature branch, implement and test the Vercel runtime, configure production/preview variables from the local ignored environment, deploy a preview, smoke-test it, then promote the verified deployment and push the source branch to GitHub. Preserve all existing MongoDB databases and the existing SQL Server project.