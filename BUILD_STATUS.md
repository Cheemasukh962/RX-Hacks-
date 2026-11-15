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

## Phase 2: Dev A, ML classifier, done and tested (local)

`cd backend && python -m pytest -q` → **34 passed** (3 new tests exercise the real model).

- **Model:** `paraphrase-multilingual-MiniLM-L12-v2` (exactly as planned) run through `fastembed`/ONNX, **no PyTorch**. Per-label `SGDClassifier(log_loss)`. Training takes about 10–50 s on CPU. The model downloads on first run to `backend/ml/.cache/` (gitignored, ~470 MB).
- **Teach-back** reads the answer **together with the instruction** ("two drops" is only wrong if the plan says one). Rules decide every number they can parse; ML fills the gaps ("until my eye stops bugging me", "with each meal"). `pathway` reports which one decided.
- **Barrier:** keyword rules ∪ ML. **Live `partial_fit`** on patient corrections → `model_updated: true`. `/demo/reset` reloads the trained weights.
- **Commands:** `python -m ml.build_dataset && python -m ml.train` (train also runs `ml.evaluate` → `ml/artifacts/eval_results.json`, served by `GET /api/eval`).

**Synthetic test split (optimistic, same templates as training):**

| System | Teach-back micro-F1 | exact | Barrier micro-F1 | exact |
|---|---|---|---|---|
| Keyword baseline | 0.547 | 60/114 | 0.804 | 40/70 |
| Rules only | 0.906 | 100/114 | — | — |
| ML only | 0.800 | 79/114 | 0.972 | 64/70 |
| **ML + rules (API)** | **0.985** | **112/114** | 0.968 | 63/70 |

**Update: training data upgraded** (synthetic 730 + **721 OpenAI paraphrases** checked by the rules + **489 real Drugs.com reviews**, UCI id 462, CC BY 4.0, with LLM *silver* labels). New eval split `reviews_silver` = 211 real reviews (barrier task only, silver labels, not hand-checked):

| Real reviews (barrier) | micro-F1 | exact |
|---|---|---|
| Keyword rules | 0.473 | 98/211 |
| ML only | **0.599** (was 0.281 before real data) | 99/211 |
| ML + rules (API) | 0.580 | 86/211 |

Teach-back ML + rules on synthetic is now **113/114**. Synthetic barrier dropped slightly (0.968 → 0.938) as the model shifted toward real wording; reported as-is.

**Held-out (the honest number): NOT WRITTEN YET.** Both devs: `python -m ml.write_heldout`, 30–40 sentences each, about half Spanish. Don't read `ml/build_dataset.py` first. See [backend/ml/data/README.md](backend/ml/data/README.md).

**Demo beat (verified over HTTP):** barrier text *"Con el bebé no tengo ni un minuto para ponerme las gotas"* → `[]` → patient corrects to `schedule_conflict` → `model_updated: true` → same sentence → `["schedule_conflict"]`. A new similar sentence (*"Con los niños no me da tiempo de tomarme las pastillas"*) is also caught. `/demo/reset` reverts it.

Gotcha: from Git Bash, `curl` mangles accented characters (é, ñ), so test Spanish with the browser, `/docs`, or Python.

## Phase 2: Dev A, live OpenAI + Deepgram (keys in `backend/.env`, gitignored)

Model: `gpt-5.4-mini` (set `OPENAI_MODEL` to change). With no key, or `REXO_DISABLE_LLM=1`, everything falls back to seeded/template output with `mode: "demo"`. Tests never call OpenAI.

- **`POST /cases {documents}` → real extraction** ([extract.py](backend/app/extract.py)): redact → OpenAI structured output → **quote check** (a quote not found in the source drops the instruction) → **number check** (a number not in its own quote becomes `null`) → reconcile in code. `mode: "live"`.
  - Live eval on the 3 fixtures (`python -m ml.eval_extraction` → `ml/artifacts/extraction_eval.json`): **3/3 conflicts found, 0 false conflicts, 3 runs in a row**, all quotes grounded.
  - Unseen pasted pair (amoxicillin 10 vs 7 days) → `duration_mismatch` found; a prompt-injection line in the document was ignored.
  - Safety net: "avoid NSAIDs" is always a medication instruction (the AI once filed it as lifestyle). Dose comparison matches mg↔mg and tablet↔tablet only (stopped a false metformin conflict).
- **`POST /explain` → personalized wording** (`mode: "live"`): language, style (brief / detailed / analogy / audio / visual), reading level, the patient's opted-in context for analogies, and **only the terms this patient tapped** get defined inline. Code still checks it: every fact number must be present, no new numbers, no stop/skip/double advice. Otherwise it falls back to the template. Quotes and conflict warnings are added by code, never by the AI. A disputed fact is always shown as "documents disagree: X vs Y".
- **`POST /voice/transcribe`**: Deepgram verified with real audio. English → `nova-3 en`; **`es` and `multi` → `nova-3 multi`** (handles Spanish *and* mixed English/Spanish, e.g. "Me pongo 1 drop 2 veces al día… at work"). Spoken numbers come back as digits. Amrit: send `language` = the profile language, or `multi`.

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
- [~] Evaluation page loads real saved results with held-out counts (synthetic results saved; held-out sentences still to be written)
- [x] Preference model updates from at least one feedback event and shows its state
- [x] A corrected barrier label updates the classifier (`model_updated: true`)
- [x] Patient can report a barrier, then generate an editable briefing (backend side)
- [x] Nothing is sent to a clinician without a patient click (no send endpoint exists)
- [ ] Core flow works at phone width (Dev B)
- [~] Missing key, mic denied and OCR failure all fall back gracefully (backend returns clear 503/501)
- [x] Urgent-symptom text triggers the "get help now" message (barrier, ask, teachback)
- [ ] Tests pass; hosted URL verified
