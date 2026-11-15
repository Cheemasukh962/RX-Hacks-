# Build status — Amrit / frontend

Updated November 15, 2026. Frontend implemented locally; deployment and backend integration remain pending. PLAN.md's frozen contracts were not changed.

## Implemented and checked

- Next.js + TypeScript + Tailwind frontend with a shadcn-style Radix/CVA Button, responsive step navigation, English/Spanish UI, and persistent synthetic banner.
- All ten planned screens, three seeded cases, typed API client, and environment-controlled FastAPI connection.
- Synthetic text paste/upload, preview and identifier-line redaction. Limited deterministic seeded parsing changes with supported input; unsupported input remains empty.
- Source-verified instruction cards, both quotes for conflicts, unknown fields, and patient-reported session checklist with conflicted tasks locked.
- Source-preserving explanations, term feedback, browser read-aloud, EN/ES rules-based teach-back, barrier confirmation/correction, editable concern log and learning profile.
- Patient-selected message content, editable English/patient-language drafts, and working clipboard copy. No send action.
- Urgent-text interruption, demo/profile reset, error states, typed fallback, and backend adapters for voice/photo.
- Honest evaluation empty state and full saved-response viewer. No invented benchmark results or demo classifier training claims.

## Validation actually run

- `npm run typecheck` — passed.
- `npm run build` — passed (Next.js webpack production build).
- `npm test` — 20/20 passed again after final UI refinements; production build and TypeScript check also passed on the final source.
- Desktop Chrome smoke: cornea care plan, both conflict quotes, explanation/term tap, conflict-first teach-back, barrier confirmation, concern included in draft, clipboard-copy success.
- Chrome iPhone 16 emulation at 393 × 852: responsive message screen, Spanish controls, urgent-text interruption, reset dialog and successful reset.
- Local preview served at `http://127.0.0.1:3000`. See README for restart command.

## Pending / integration handoff

- **Vercel deployment:** no connected Vercel account/project is available in this session. Vercel integration was offered. Project root must be `frontend`. Hosted URL: not yet deployed.
- **FastAPI:** no backend files or deployed endpoint were present when implementation began. Set `NEXT_PUBLIC_API_URL` and allow the frontend origin in backend CORS.
- **Backend-only features:** full extraction/Q&A, ML classification and `partial_fit`, adaptive style selection, real saved evaluation/simulation artifacts, Deepgram, OCR. Their client adapters are implemented; live behavior is unverified.
- **Evaluation:** inner JSON shape is not specified by the frozen plan. Current screen preserves the raw saved response. A dedicated metric/chart layout awaits actual artifacts.
- **Human-held-out sentences:** the 30–40 sentences assigned to Amrit still need human authorship/review; frontend unit fixtures are not a substitute for the held-out ML set.
- Physical-phone and hosted end-to-end acceptance, backup recording, and rehearsal remain pending.

## Plan acceptance checklist

- [ ] App starts locally with one command per service; `.env.example` lists every key — frontend starts; backend unavailable.
- [x] Demo selector loads a synthetic AVS + note pair.
- [x] Pasting different supported text changes the seeded extracted result; full extraction awaits backend.
- [x] Every displayed medication instruction has a verified source quote.
- [x] Lisinopril 10 mg vs 20 mg flagged with both quotes (automated).
- [x] Ibuprofen continue vs avoid flagged; no choice made (automated).
- [x] Matching pair produces zero conflicts (automated).
- [x] Missing fields show unknown rather than invented values.
- [x] Language/detail changes preserve instructions and citations (automated).
- [x] Typed teach-back runs; wrong frequency detected on non-conflicting pair (automated); source-conflict flow verified in Chrome.
- [ ] Evaluation loads real held-out results — awaits backend artifacts.
- [x] Feedback updates visible preference state.
- [ ] Corrected barrier trains classifier — deliberately false in seeded mode; awaits backend.
- [x] Patient can report a barrier and generate/edit/copy a briefing.
- [x] Nothing is sent to a clinician by the frontend.
- [x] Responsive layout checked at phone width in Chrome emulation; physical phone pending.
- [ ] Missing key, mic denial, and OCR failure all fall back — seeded path implemented; live error scenarios unverified.
- [x] Urgent text interrupts normal flow (automated and Spanish mobile browser check).
- [ ] Tests pass and hosted URL verified — local tests/build pass; hosting pending.
