# REXO — The Patient Safety Loop

Synthetic-data hackathon build. See [PLAN.md](PLAN.md) for the full plan and [BUILD_STATUS.md](BUILD_STATUS.md) for live status.

## Backend (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env              # fill in keys (optional; missing keys = demo mode)
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health
- Tests: `python -m pytest -q` (from `backend/`)

### Deploy (Render)

`render.yaml` at the repo root defines the service. On Render: **New → Blueprint →** pick this repo. Set `OPENAI_API_KEY` / `DEEPGRAM_API_KEY` in the dashboard (never commit them). Health check: `/api/health`.

## Frontend (Next.js)

Owned by Dev B. Set `NEXT_PUBLIC_API_URL` to the backend URL.
