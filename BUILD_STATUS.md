# BUILD_STATUS

_Last updated: Nov 15, 2026. `phase-1-sukh` (backend, Phases 1–2) and `phase1Amrit` (frontend) merged into `main`._

## Verified on `main` after the merge

- Backend: `cd backend && python -m pytest -q` → **41 passed**.
- Frontend: `npm run typecheck` ✅, `npm test` → **20/20** ✅, `npm run build` ✅.
- Contract smoke (FastAPI TestClient, using the exact payloads the frontend sends): case load, profile create/PUT, teach-back, thumbs, barrier → `label_confirm` (`model_updated: true`), briefing with selected concern + conflict, photo 501, voice 503 with readable message, `/eval` shape. All OK.
- **Not yet verified:** the frontend running in a browser against the real backend (`NEXT_PUBLIC_API_URL` set). Everything above is API level.

### Contract mismatches fixed during the merge

| Mismatch | Fix |
|---|---|
| Multipart field: backend `file`, frontend `audio` / `image` (PLAN says "multipart audio/image") | Backend now reads `audio` (voice) and `image` (photo) |
| `PatientProfile.concerns`: backend objects, UI strings | Adapter in `frontend/lib/api.ts` (keeps ids/labels for unchanged text) |
| `slot_check`: backend strings, UI booleans | Adapter maps `correct/incorrect/…`; UI shows "Documents disagree" |
| Thumbs payload: UI `{helpful}`, backend `{up}` | UI sends `{style, up}` (mock accepts both) |
| `quantity`: backend string, UI number | UI type widened |
| Profile PUT ignored `teach_back_history` | Added to `ProfilePatch` (UI "clear history" now works) |
| Backend error `detail` hidden behind a generic message | UI shows the backend's patient-readable `detail` |
| Profile PUT emitted a pydantic serialization warning | `_apply_patch` re-validates merged data |

## Deploy URLs

- Backend: _not deployed._ `render.yaml` ready → Render: New → Blueprint → this repo. Set keys in the dashboard.
- Frontend: _not deployed._ Vercel, Root Directory `frontend`, set `NEXT_PUBLIC_API_URL` to the Render URL before building.

## What exists

**Backend** (details in git history / previous status): all section 6 routes; fixtures for 3 cases with test-enforced quotes; `reconcile.py`; redaction; EN/ES urgent check; live OpenAI extraction with quote + number checks (3/3 conflicts, 0 false, on fixtures); personalized `/explain` with fact check and template fallback; teach-back = rules + ML (`pathway` reported); barrier = rules ∪ ML with live `partial_fit` (`model_updated: true`); Thompson style bandit + term scores; Deepgram transcription (`nova-3`, `multi` for ES / code-switching); demo mode with no keys.

**Frontend:** Next.js + TS + Tailwind; all 10 screens; EN/ES UI; 3 seeded cases; full offline mock of the API; paste/upload with redaction preview; source-quote cards and conflict cards with both quotes; checklist with conflicted tasks locked; explanation + term tap + read-aloud; teach-back; barrier confirm/correct; editable concern log; editable/copyable briefing (no send); learning profile; evaluation viewer; urgent-text interruption; reset; mic recorder → `/voice/transcribe`; photo → `/ingest/photo`. Phone width checked in Chrome emulation (393×852).

## Remaining work, split by branch

Both branches start from the same `main` (merge commit `4a7869a`). Work on your own branch, keep PLAN.md section 5/6 contracts stable, and merge back into `main` through a PR. If you need to change an API shape, say so first and update `frontend/lib/api.ts` + `backend/app/schemas.py` together.

### `sukh` branch: backend / ML / deploy (Sukhman)

Must do
- [ ] Deploy backend to Render (`render.yaml` → New → Blueprint). Set `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `CORS_ORIGINS` (add the Vercel URL once Amrit has it). Put the backend URL in "Deploy URLs" above
- [ ] Write your 30–40 held-out sentences (`python -m ml.write_heldout`, ~half Spanish, without reading `ml/build_dataset.py`). After Amrit's are in too, re-run `python -m ml.train` and commit the new `ml/artifacts/eval_results.json`
- [ ] `ml/simulate_bandit.py` → `ml/artifacts/bandit_sim.json`: 100 simulated patients, adaptive vs fixed style, labeled as a simulation. Tell Amrit the JSON shape
- [ ] Check that Render can download the ~470 MB embedder on first start (disk + startup time); if not, pre-download it in the build command

Nice to have
- [ ] Call `learning.mark_term_known` when a teach-back answer uses a term correctly (the function exists but nothing calls it)
- [ ] Optional LLM polish for the `/briefing` draft (template fallback stays; quotes are still added by code)

Stretch (only if the core is stable)
- [ ] Photo intake: `vision.py` (OpenCV flatten/deskew/redact) + Tesseract → `/ingest/photo` (currently returns 501)
- [ ] Refill estimate when quantity and frequency are both documented (backend field; Amrit displays it)

### `amrit` branch: frontend / UX (Amrit)

The frontend works end to end: all 10 screens, the offline mock, and the API adapters are in place. The work here is UX design plus the items below.

Must do
- [ ] Run against the real backend (`frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`) and click through the full demo script. Report any contract mismatch to Sukhman
- [ ] UX / design pass on all screens (keep: source quotes, both quotes on conflicts, no send button, synthetic banner, urgent interruption)
- [ ] Evaluation screen: replace the raw JSON viewer with tables (F1 + exact-match counts with denominators per split, labeled synthetic / silver / held-out). Shape: `{available, eval_results, bandit_sim, mode}`; sample in `backend/ml/artifacts/eval_results.json`
- [ ] Bandit simulation chart on the evaluation screen, labeled "simulation" (once Sukhman's `bandit_sim.json` exists)
- [ ] Write your 30–40 held-out sentences (`cd backend && python -m ml.write_heldout`, ~half Spanish, don't read `ml/build_dataset.py`)
- [ ] Deploy to Vercel (Root Directory `frontend`, `NEXT_PUBLIC_API_URL` = Render URL). Send Sukhman the Vercel URL for `CORS_ORIGINS`. Put it in "Deploy URLs" above
- [ ] In the browser, check the error paths: no keys (demo mode), mic permission denied, voice failure message, photo 501 → paste text

Nice to have
- [ ] Learning screen: small bandit-state chart plus a before/after view for the demo
- [ ] Make it clear on screen that editing a concern does not retrain the classifier

Stretch
- [ ] "Why it matters" illustrative SVG for the cornea case (labeled illustrative)
- [ ] Email recap via `mailto:` (opt-in)

### Together, after both branches merge into `main`
- [ ] Full acceptance checklist below on the hosted URL, on a physical phone
- [ ] Record a backup screen video; rehearse the 3-minute script twice

## Acceptance checklist (PLAN section 11), combined

- [x] App starts locally with one command per service; `.env.example` lists every key
- [x] Demo selector loads a synthetic AVS + note pair (backend + seeded frontend)
- [~] Pasting different text changes the extracted result — backend live extraction works (needs `OPENAI_API_KEY`); seeded frontend handles supported text only; **not yet clicked through connected**
- [x] Every medication claim shows a matching source quote (backend test-enforced; frontend re-verifies)
- [x] Lisinopril 10 mg vs 20 mg flagged with both quotes
- [x] Ibuprofen continue vs avoid flagged; no choice made for the patient
- [x] Matching pair produces zero conflicts
- [x] Missing fields show `unknown`, never an invented value
- [x] Changing language or detail level never changes dose or frequency (unit tests both sides)
- [x] Judge can type a teach-back answer, including a wrong frequency, and get the right outcome
- [ ] Evaluation page loads real saved results **with held-out counts** — held-out sentences not written; screen shows raw JSON
- [x] Preference model updates from at least one feedback event and shows its state
- [x] A corrected barrier label updates the classifier (`model_updated: true`) — backend; seeded frontend honestly returns `false`
- [x] Patient can report a barrier, then generate, edit and copy a briefing
- [x] Nothing is sent to a clinician without a patient click (no send endpoint, no send button)
- [~] Core flow works at phone width — Chrome emulation only; physical phone pending
- [~] Missing key, mic denied and OCR failure all fall back gracefully — backend returns clear 503/501 and UI now shows them; browser check pending
- [x] Urgent-symptom text triggers the "get help now" message (backend: barrier/ask/teachback; frontend interruption)
- [ ] Tests pass; **hosted URL verified** — tests pass; nothing hosted yet

## Notes / gotchas

- Keys live in `backend/.env` (gitignored) or the Render dashboard. **Never in chat, git, or `NEXT_PUBLIC_*`.**
- From Git Bash, `curl` mangles accented characters; test Spanish via the browser, `/docs`, or Python.
- First ML request downloads the embedder (~470 MB) to `backend/ml/.cache/`; Render needs the disk/time for that.
- Unknown `profile_id` on explain/teachback/barrier/ask is auto-created; unknown case → 404 `{detail}`.
