# REXO — The Patient Safety Loop

Your care, understood. Your concerns, heard.

Synthetic-data patient-safety demo for HackRx 2026. See [PLAN.md](PLAN.md) for the product, frozen data/API contracts, and team responsibilities, and [BUILD_STATUS.md](BUILD_STATUS.md) for live status and the remaining checklist. Sukhman owns the FastAPI/data/ML lane (`backend/`); Amrit owns the frontend (`frontend/`).

## Run the backend (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env              # fill in keys (optional; missing keys = demo mode)
uvicorn app.main:app --reload --port 8000
```

- API docs (every request/response shape): http://localhost:8000/docs
- Health: http://localhost:8000/api/health
- Tests: `python -m pytest -q` (from `backend/`)
- ML: `python -m ml.build_dataset && python -m ml.train` (train also runs the evaluation → `ml/artifacts/eval_results.json`, served by `GET /api/eval`)
- Bandit simulation: `python -m ml.simulate_bandit` → `ml/artifacts/bandit_sim.json` (labeled simulation, also served by `/api/eval`)
- Live end-to-end check: `python scripts/smoke_live.py [backend-url]` (server must be running)

## Run the frontend (Next.js)

Requires Node.js 22+ and npm.

```sh
cd frontend
npm ci
npm run dev        # http://127.0.0.1:3000
npm run typecheck
npm test
npm run build && npm start
```

No API keys are needed for the seeded demo: with `NEXT_PUBLIC_API_URL` unset, `frontend/lib/mock.ts` serves the same routes locally. The webpack build is intentional (Turbopack's CSS worker needs process sockets unavailable in some restricted environments).

## Connect frontend to backend

Copy `frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The client appends `/api` if missing. Restart the dev server (or rebuild) after changing it, and allow the frontend origin in the backend's `CORS_ORIGINS`. Only this public URL belongs in frontend env vars; `OPENAI_API_KEY` / `DEEPGRAM_API_KEY` stay on the backend.

`frontend/lib/api.ts` is the only transport boundary. It adapts a few backend shapes to what the UI uses:

- `PatientProfile.concerns`: backend `{id, text, labels, confirmed}` ↔ UI plain strings (ids/labels are preserved for unchanged text).
- `slot_check`: backend `"correct" | "incorrect" | "not_mentioned" | "not_documented" | "documents_disagree"` → UI `true | false | null | "documents_disagree"`.
- Backend error `detail` messages (e.g. "Voice input is not configured. Please type your answer instead.") are shown to the user.

Other contract details: multipart fields are `audio` + `language` for `/voice/transcribe` and `image` for `/ingest/photo`; thumbs feedback payload is `{style, up}`; briefing `include.concerns` takes concern text or ids, `include.conflicts` takes conflict ids; `/eval` returns `{available, eval_results, bandit_sim, mode}`.

## Deploy

- **Backend (Render):** `render.yaml` at the repo root defines the service. New → Blueprint → pick this repo. Set `OPENAI_API_KEY` / `DEEPGRAM_API_KEY` in the dashboard (never commit them). Health check: `/api/health`.
- **Frontend (Vercel):** import the repo, Root Directory **`frontend`**, framework Next.js, install `npm ci`, build `npm run build`. Set `NEXT_PUBLIC_API_URL` to the Render URL before building (leave unset for the seeded-only demo). Then add the Vercel origin to the backend's `CORS_ORIGINS`.

## Safety notes

Only synthetic documents may be entered. Identifier-line redaction is a courtesy and does not establish privacy compliance. Every displayed instruction quote is verified against the supplied document, unresolved conflicts are preserved (REXO never picks a side), and recognized urgent text pauses normal flows. Nothing is sent to a clinician without a patient click. This is not clinical validation.

Manual smoke check: [frontend/tests/SMOKE.md](frontend/tests/SMOKE.md).
