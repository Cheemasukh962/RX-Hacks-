# BUILD_STATUS

_Last updated: Nov 15, 2026 by Dev A (Sukhman), Phase 1._

## Deploy URLs

- Backend: _not deployed yet._ `render.yaml` is ready. Needs someone logged in to Render: New → Blueprint → this repo.
- Frontend: _Dev B_

## Phase 1: Dev A (backend), done and tested

`cd backend && python -m pytest -q` → **31 passed** (also smoke-tested over real HTTP with uvicorn, CORS preflight OK).

| Item | Status |
|---|---|
| `schemas.py`: section 5 + section 6 models | ✅ |
| `store.py`: in-memory state, fixture loading, `/demo/reset` | ✅ |
| `main.py`: **every route in section 6** exists | ✅ |
| Fixtures: cornea, medication, **matching (case 3)** + `*.expected.json` | ✅ quotes verified character for character by test |
| `reconcile.py` + tests: cornea = 1 `frequency_mismatch`; medication = `dose_mismatch` + `action_mismatch`; matching = 0 | ✅ |
| `ingest.py`: doc typing (headings) + name/DOB/MRN redaction | ✅ |
| `safety.py`: urgent-symptom check (EN + ES), numeric fact check, prompt wrapper | ✅ |
| Deploy backend | ⏳ config ready, needs a Render login |

### What each route does right now (all honest, all `mode: "demo"`)

| Route | Phase 1 behaviour | Upgraded in |
|---|---|---|
| `GET /demo-cases`, `POST /cases {demo_case_id}`, `GET /cases/{id}` | Real: fixtures → reconcile → tasks | — |
| `POST /cases {documents}` | Pasting a seeded pair reproduces it. Other text is typed and redacted, but `instructions: []` (nothing invented) | Phase 2 `extract.py` |
| `/profile*` | Real: create / get / put / reset; bandit seeded from onboarding choice | — |
| `POST /explain` | Deterministic template from fields + quotes, EN/ES, tap-to-define glossary, fact check. Conflicts show both quotes | Phase 2 LLM wording |
| `POST /ask` | Keyword lookup over instructions → quotes, or "not in your documents"; urgent short-circuit | Phase 2 |
| `POST /teachback` | **Rules pathway** (`pathway: "rules"`): EN/ES number/frequency parsing, slot check, source-conflict rule | Phase 2 ML → `"both"` |
| `POST /barrier` | Keyword rules EN/ES + urgent check; saves the concern to the profile | Phase 3 ML |
| `POST /feedback` | Real: thumbs / term_tap / style_change update profile; label_confirm/correct stored. `model_updated: false` until partial_fit exists | Phase 3 |
| `POST /briefing` | Template draft EN + patient language with quotes and concerns. Copy only | Phase 3 LLM polish |
| `POST /voice/transcribe` | Calls Deepgram if `DEEPGRAM_API_KEY` is set; otherwise 503 "please type" | — |
| `POST /ingest/photo` | 501 "paste text instead" | Phase 4 stretch |
| `GET /eval` | Returns saved artifacts, or `available: false` (no fake numbers) | Phase 2/3 |

## Notes for Dev B (Amrit): contract details the plan left open

1. **`GET /demo-cases`** returns an array (per contract). Each item also has `mode`.
2. **`PatientProfile.concerns`** is a list of objects: `{id, text, labels[], confirmed}`. `id` equals the `example_id` from `/barrier`.
3. **`/briefing` `include.concerns`** takes concern ids (or raw text). `include.conflicts` takes conflict ids (`"c1"`).
4. **`slot_check` values:** `"correct" | "incorrect" | "not_mentioned" | "not_documented" | "documents_disagree"`.
5. **`defined_terms`:** `[{term, definition}]`. **`citations`:** `[{document_id, quote}]`.
6. **`/feedback` payloads:** thumbs `{style?, up}`, term_tap `{term}`, style_change `{style}`, label_confirm `{example_id}`, label_correct `{example_id, labels[]}`.
7. **`/eval`:** `{available, eval_results, bandit_sim, mode}`.
8. **Errors:** 404 `{detail}` for unknown case / instruction / profile (GET). Unknown `profile_id` on explain/teachback/barrier/ask is auto-created.
9. Live interactive docs with every shape: `<backend>/docs`.

## Blocked / needs a human

- Render login to deploy (see README).
- OpenAI + Deepgram keys go in the Render dashboard / `backend/.env`. **Never in chat or in git.**

## Acceptance checklist (section 11)

- [x] App starts locally with one command per service; `.env.example` lists every key (backend)
- [x] Demo selector loads a synthetic AVS + note pair (backend)
- [ ] Pasting different text changes the extracted result (Phase 2 extract)
- [x] Every medication claim shows a matching source quote (fixtures; test-enforced)
- [x] Lisinopril 10 mg vs 20 mg flagged with both quotes
- [x] Ibuprofen continue vs avoid flagged; no choice made for the patient
- [x] Matching pair produces zero conflicts
- [x] Missing fields show `unknown`, never an invented value (explain: "not in your documents")
- [x] Changing language or detail level never changes dose or frequency (unit test)
- [x] Judge can type a teach-back answer, including a wrong frequency, and get the right outcome (rules pathway)
- [ ] Evaluation page loads real saved results with held-out counts
- [x] Preference model updates from at least one feedback event and shows its state
- [ ] A corrected barrier label updates the classifier (`model_updated: true`) (Phase 3)
- [x] Patient can report a barrier, then generate an editable briefing (backend side)
- [x] Nothing is sent to a clinician without a patient click (no send endpoint exists)
- [ ] Core flow works at phone width (Dev B)
- [~] Missing key, mic denied and OCR failure all fall back gracefully (backend returns clear 503/501)
- [x] Urgent-symptom text triggers the "get help now" message (barrier, ask, teachback)
- [ ] Tests pass; hosted URL verified
