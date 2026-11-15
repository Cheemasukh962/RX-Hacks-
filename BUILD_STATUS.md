# BUILD_STATUS

_Last updated: Nov 15, 2026. `main` = `sukh` (backend through `90ddbe9`) + `amrit` (frontend `3bc19db`), merged, plus backend fixes from the full browser run._

## Verified on `main` after the latest merge

- Backend: `cd backend && python -m pytest -q` → **48 passed** (includes ML classifier tests).
- Frontend: `npm run typecheck` ✅, `npm test` → **21/21** ✅, `npm run build` ✅.
- **Full browser run, everything on** (Chrome driven by Playwright; frontend on `NEXT_PUBLIC_API_URL=http://localhost:8000`; backend with ML classifier + live OpenAI + Deepgram): **34/34 checks pass**:
  - cornea case + conflict card with both quotes; preferences saved
  - live OpenAI explanation (fact check passed, names the disagreement); header shows "Connected care service"
  - term tap lowers term score; thumbs saved; question answered from documents with both quotes
  - teach-back "two drops twice a day" → `dose_error` + source conflict, slot results + pathway shown
  - **voice:** Chrome fake mic → Deepgram → transcript lands in the teach-back box
  - Spanish barrier sentence → `[]` → patient corrects to Schedule → "classifier was updated" → same sentence → `schedule_conflict`; "the drops cost too much" still only `cost`
  - briefing with selected concern + both conflict quotes, copy to clipboard works, no send button
  - learning profile + concern log; evaluation tables with denominators + simulation labeled as simulation
  - pasted medication documents → live OpenAI extraction → both conflicts and cards
  - Spanish UI → live Spanish explanation that passes the fact check, shown in the UI
  - urgent text ("chest pain and trouble breathing") → GET HELP NOW
- The driver script lives outside the repo (`C:/Users/cheem/rexo-e2e/flow.js`, needs `playwright-core` + installed Chrome). Backend-only check: `python scripts/smoke_live.py [url]`.
- **Not yet verified:** mic-permission-denied and photo error paths in the browser; physical phone; anything hosted.

### Bugs found by the browser run and fixed (backend)

| Bug | Effect | Fix |
|---|---|---|
| Fact checker read REXO's own sentence "Your **two** documents disagree" / "Sus **dos** documentos" as the number 2 | Every explanation of a conflict whose quotes contain no "2" failed `fact_check`, so the **frontend refused to show it**. That covered the whole blood-pressure demo case (lisinopril/ibuprofen), seeded and live | The fixed conflict sentence is excluded before the number check (regression test, EN + ES) |
| OpenAI wording used count words ("one says…, the other…", "two routes") or left out the disputed values | Live explanations silently fell back to the template: 16/70 across styles/languages/instructions | Prompt: no count words, name each document, state each document's value; analogies are about the medicine, not the disagreement. Now **69/70 live**; the remaining fallback is the guardrail correctly catching "2 weeks" from an uncited part of the note |
| `_mode()` was still the Phase 1 stub (always `"demo"`) | Header said "Demo mode (seeded)" even with live keys | `"live"` when the OpenAI key is configured, per PLAN rule 10 (cases/explain still report per response) |

Frontend (cosmetic, for Amrit): `/favicon.ico` 404s on every page load.

### Latest merge: what each branch brought

**`sukh` (backend):**
- Fixed: one barrier correction no longer adds its label to every later sentence (small learning rate + replay; regression test).
- `ml/simulate_bandit.py` → `bandit_sim.json`, served by `/api/eval`.
- A term used in a correct teach-back is marked known.
- `scripts/smoke_live.py` end-to-end check.

**`amrit` (frontend):**
- Applied muted slate blue (#34516d), shaded mist (#e0e7ee), neutral ivory (#f7f5f0), and off-white cards (#fdfcf9). Conflict/urgent colors remain distinct.
- Default explanation requests now allow the backend style bandit to choose. The patient can disable automatic choice and explicitly select brief/detailed.
- Expanded EN/ES urgent guard to cover backend phrases and stop teach-back when the backend returns emergency guidance, without changing the frozen API.
- Fixed startup after a backend restart: stale profile 404 creates a fresh profile; other service errors remain visible.
- Replaced raw evaluation JSON with dataset-separated comparison tables, exact-match numerators/denominators, micro/macro F1, precision, recall, and expandable per-label support. Raw artifacts remain inspectable.
- Concern-log editing now explicitly says it does not train the classifier.
- Validation: 21 frontend tests and TypeScript passed; final production build passed after all refinements. 38 backend API/extraction/reconciliation tests passed in an isolated environment; ML classifier tests were not run.
- Connected Chrome check against local FastAPI with REXO_DISABLE_ML=1 and REXO_DISABLE_LLM=1: stale-session recovery, backend case load, adaptive explanation selection with both quotes, evaluation tables including 113/114 synthetic teach-back exact matches and explicit missing human-held-out data.
- Still required: actual ML/live-service browser checks; mic denial and voice/photo error-path checks; human-authored held-out examples; deployed Render/Vercel URLs and physical-phone acceptance. No held-out or simulation data was fabricated.

### Contract mismatches fixed during the first merge

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

**Frontend:** Next.js + TS + Tailwind; all 10 screens; EN/ES UI; 3 seeded cases; full offline mock of the API; paste/upload with redaction preview; source-quote cards and conflict cards with both quotes; checklist with conflicted tasks locked; explanation + term tap + read-aloud; teach-back; barrier confirm/correct; editable concern log; editable/copyable briefing (no send); learning profile; evaluation tables per split; urgent-text interruption; reset; mic recorder → `/voice/transcribe`; photo → `/ingest/photo`. Phone width checked in Chrome emulation (393×852).

## Remaining work, split by branch

Both branches should start again from the current `main` (pull `main` into your branch first). Work on your own branch, keep PLAN.md section 5/6 contracts stable, and merge back into `main` through a PR. If you need to change an API shape, say so first and update `frontend/lib/api.ts` + `backend/app/schemas.py` together.

### `sukh` branch: backend / ML / deploy (Sukhman)

Must do
- [x] Live end-to-end check of every main feature: `python scripts/smoke_live.py [url]` → 23/23 with real OpenAI + Deepgram keys (re-run it against the Render URL after deploy)
- [x] Fixed: one barrier correction used to add its label to every later sentence (live update now uses a small learning rate + replay of training data; regression test)
- [ ] Deploy backend to Render (`render.yaml` → New → Blueprint). Set `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `CORS_ORIGINS` (add the Vercel URL once Amrit has it). Put the backend URL in "Deploy URLs" above
- [ ] Write your 30–40 held-out sentences (`python -m ml.write_heldout`, ~half Spanish, without reading `ml/build_dataset.py`). After Amrit's are in too, re-run `python -m ml.train` and commit the new `ml/artifacts/eval_results.json`
- [x] `ml/simulate_bandit.py` → `ml/artifacts/bandit_sim.json` (`python -m ml.simulate_bandit`, ~3 s). Runs the production bandit code on 100 simulated patients × 20 teach-backs, repeated over 20 seeds, against "fixed onboarding style" and "random". Result: adaptive goes from 62% → 71% teach-back success (first 5 vs last 5 rounds) and ends on the patient's best style 79% of the time; fixed stays flat at 64% and is on the best style for 39%. Overall success is 67.2% vs 63.6% (adaptive pays an exploration cost early). Served by `GET /api/eval` as `bandit_sim`
  - **Shape for Amrit's chart:** `bandit_sim.label` (show it, it says SIMULATION), `bandit_sim.policies.{adaptive,fixed,random}.success_by_round` (20 numbers, 0–1, plot as lines), `.teachback_success_rate.{mean,min,max}`, `.ends_on_best_style.{mean,min,max}`, `bandit_sim.denominators`, `bandit_sim.assumptions`
- [ ] Check that Render can download the ~470 MB embedder on first start (disk + startup time); if not, pre-download it in the build command

Nice to have
- [x] Term used in a correct teach-back (English or Spanish alias, e.g. "hipertensión") → `mark_term_known`. Only on `understood`, never on a wrong answer. Tested
- [ ] Optional LLM polish for the `/briefing` draft (template fallback stays; quotes are still added by code)

Stretch (only if the core is stable)
- [ ] Photo intake: `vision.py` (OpenCV flatten/deskew/redact) + Tesseract → `/ingest/photo` (currently returns 501)
- [ ] Refill estimate when quantity and frequency are both documented (backend field; Amrit displays it)

Later: come back after the original backend is done
- [ ] **Targeted re-explain (adapt to what the patient misunderstood).** Today OpenAI gets the bandit-picked style, language, opted-in context and tapped terms, but never *what* the patient got wrong. The bandit only learns "this style missed".
  - After a wrong teach-back, store the mismatched slot per instruction on the profile (e.g. `{instruction_id, slot: "frequency", said: 2, documented: 4}`). It is derived from `slot_check` + labels in `/teachback`.
  - `/explain` for that instruction leads with the misunderstood slot and passes it to OpenAI as "patient thought X; document says Y". Send only the structured mismatch, never the raw answer text.
  - Adaptive reading level: drop from ~6th grade to simpler wording after repeated misses on the same instruction; go back up after an `understood`.
  - Keep every guardrail: the code fact check still verifies all numbers, the template fallback stays, and conflicts still show both quotes.
  - Needs no API contract change (internal profile field + explain prompt), so the frontend is untouched.
  - Demo beat: wrong teach-back → explanation focuses on frequency → correct teach-back → `understood`.
  - About an hour of work. Add tests: the mismatch is recorded, explain mentions the slot, and numbers are unchanged.

### `amrit` branch: frontend / UX (Amrit)

The frontend works end to end: all 10 screens, the offline mock, and the API adapters are in place. The work here is UX design plus the items below.

Must do
- [x] Run against the real backend and click through the full demo script — done with everything on (34/34, see top)
- [~] UX / design pass on all screens — slate blue / ivory theme applied; continue (keep: source quotes, both quotes on conflicts, no send button, synthetic banner, urgent interruption)
- [x] Evaluation screen: tables per split (exact matches with denominators, micro/macro F1, precision, recall, per-label), held-out shown as missing until written
- [ ] Bandit simulation chart on the evaluation screen, labeled "simulation". The artifact now exists (`backend/ml/artifacts/bandit_sim.json`); the screen currently shows it as raw JSON. Shape is documented under the `sukh` section above
- [ ] Write your 30–40 held-out sentences (`cd backend && python -m ml.write_heldout`, ~half Spanish, don't read `ml/build_dataset.py`)
- [ ] Deploy to Vercel (Root Directory `frontend`, `NEXT_PUBLIC_API_URL` = Render URL). Send Sukhman the Vercel URL for `CORS_ORIGINS`. Put it in "Deploy URLs" above
- [ ] Add `frontend/app/icon` / favicon (404 on every load, cosmetic)
- [ ] In the browser, check the error paths: no keys (demo mode), mic permission denied, voice failure message, photo 501 → paste text

Nice to have
- [ ] Learning screen: small bandit-state chart plus a before/after view for the demo
- [x] Make it clear on screen that editing a concern does not retrain the classifier

Stretch
- [ ] "Why it matters" illustrative SVG for the cornea case (labeled illustrative)
- [ ] Email recap via `mailto:` (opt-in)

### Together, after both branches merge into `main`
- [ ] Full acceptance checklist below on the hosted URL, on a physical phone
- [ ] Record a backup screen video; rehearse the 3-minute script twice

## Acceptance checklist (PLAN section 11), combined

- [x] App starts locally with one command per service; `.env.example` lists every key
- [x] Demo selector loads a synthetic AVS + note pair (backend + seeded frontend)
- [x] Pasting different text changes the extracted result — verified in the browser with live OpenAI extraction
- [x] Every medication claim shows a matching source quote (backend test-enforced; frontend re-verifies)
- [x] Lisinopril 10 mg vs 20 mg flagged with both quotes
- [x] Ibuprofen continue vs avoid flagged; no choice made for the patient
- [x] Matching pair produces zero conflicts
- [x] Missing fields show `unknown`, never an invented value
- [x] Changing language or detail level never changes dose or frequency (unit tests both sides)
- [x] Judge can type a teach-back answer, including a wrong frequency, and get the right outcome
- [~] Evaluation page loads real saved results **with held-out counts** — tables load real saved results; held-out sentences not written yet; simulation chart pending
- [x] Preference model updates from at least one feedback event and shows its state
- [x] A corrected barrier label updates the classifier (`model_updated: true`) — backend; seeded frontend honestly returns `false`
- [x] Patient can report a barrier, then generate, edit and copy a briefing
- [x] Nothing is sent to a clinician without a patient click (no send endpoint, no send button)
- [~] Core flow works at phone width — Chrome emulation only; physical phone pending
- [~] Missing key, mic denied and OCR failure all fall back gracefully — backend returns clear 503/501 and UI now shows them; browser check pending
- [x] Urgent-symptom text triggers the "get help now" message (backend: barrier/ask/teachback; frontend guard expanded to match backend phrases and emergency replies)
- [ ] Tests pass; **hosted URL verified** — tests pass; nothing hosted yet

## Notes / gotchas

- Keys live in `backend/.env` (gitignored) or the Render dashboard. **Never in chat, git, or `NEXT_PUBLIC_*`.**
- From Git Bash, `curl` mangles accented characters; test Spanish via the browser, `/docs`, or Python.
- First ML request downloads the embedder (~470 MB) to `backend/ml/.cache/`; Render needs the disk/time for that.
- Unknown `profile_id` on explain/teachback/barrier/ask is auto-created; unknown case → 404 `{detail}`.
