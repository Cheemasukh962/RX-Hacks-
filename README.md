# REXO

Your care, understood. Your concerns, heard.

Synthetic patient-safety demo for HackRx 2026. See [PLAN.md](PLAN.md) for the product, frozen data/API contracts, and team responsibilities. Amrit owns the frontend; Sukhman owns the FastAPI/data/ML lane.

## Run the frontend

Requires Node.js 22+ and npm. From the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:3000. No API keys are needed for the seeded demo.

```sh
npm run typecheck
npm test
npm run build
npm start
```

The webpack build is intentional: Turbopack's CSS worker needs process sockets unavailable in some restricted development environments. Tests use Node's `tsx` import hook to avoid an unnecessary CLI IPC server.

## Connect Sukhman's backend

Copy `frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
NEXT_PUBLIC_API_URL=https://your-backend.example.com
```

The client appends `/api` if it is missing. Restart the dev server (or rebuild the deployed app) after changing this value. Allow the frontend origin in the backend's CORS configuration. Only this public backend URL belongs in frontend environment variables. `OPENAI_API_KEY` and `DEEPGRAM_API_KEY` stay on the backend; root `.env.example` lists those names.

`frontend/lib/types.ts` follows PLAN sections 5–6. `frontend/lib/api.ts` is the only transport boundary. `frontend/lib/mock.ts` implements the same routes in seeded mode. Connected responses retain their explicit `mode`; network errors never silently replace user input with a sample.

Contract details for integration:

- `/demo-cases` preserves the specified array shape (entries may carry `mode`). Object responses require `mode: "live" | "demo"`.
- Feedback's open-ended `payload` currently uses `{style, helpful}` for thumbs, `{term}` for a term tap, `{style}` for style changes, and `{example_id, text, labels}` for barrier confirmations/corrections.
- Briefing `include.concerns` contains selected patient strings; `include.conflicts` contains selected conflict IDs.
- Multipart field names are `audio` plus `language` for transcription, and `image` for photo intake.
- `defined_terms` accepts strings or `{term, definition}` objects. Original source quotes retain their original language.
- The plan leaves `/eval`'s inner schema unspecified. The screen displays the saved response intact, without manufacturing metrics or denominators. A dedicated chart can be connected once the backend artifact shape is available.
- There is no task-update route in the frozen API. Checklist completion is explicitly patient-reported, local to this browser session, and cannot resolve conflicts.

## What works without the backend

All ten screens: overview, preferences, documents, care plan, explanation, teach-back, concern capture, editable/copyable care-team message, learning profile, and evaluation status. English and Spanish UI, three fictional cases, source quotes, responsive navigation, reset, typed input, browser read-aloud, and preference/concern editing are available.

The local parser recognizes the three sample medicines (prednisolone, lisinopril, ibuprofen/NSAIDs), supported English instruction lines, follow-up dates, and fixture warning lines. Editing recognized doses/frequencies changes the result. Unrecognized text produces an empty result rather than a fabricated sample. This is a limited frontend demonstration, not the production extraction system.

Seeded teach-back uses conservative EN/ES numeric rules and identifies its pathway as `rules`. It does not claim ML confidence or clinical comprehension. Barrier confirmation saves the concern but returns `model_updated: false`. Preference feedback updates visible counters; adaptive bandit sampling and global training belong to the backend. Open-ended Q&A, Deepgram audio transcription, photo OCR, full text extraction, and saved ML evaluation require the backend. PDF users can paste extracted synthetic text.

Only synthetic documents may be entered. Identifier-line redaction is a courtesy and does not establish privacy compliance. The app verifies every displayed instruction quote against the supplied document, preserves unresolved conflicts, and pauses normal flows for recognized urgent text. This is not clinical validation.

## Deploy to Vercel

Import this repository in Vercel and choose **`frontend` as the Root Directory**, **Next.js** as the framework, `npm ci` for install, and `npm run build` for build. Use the default Next.js output directory. Leave `NEXT_PUBLIC_API_URL` unset for the seeded demo, or set it to the deployed FastAPI origin before building.

Alternatively, from an authenticated Vercel CLI in `frontend`, run `vercel` to create a preview, then `vercel --prod` when the preview is verified. Do not put service secrets in `NEXT_PUBLIC_*` variables.

Deployment is not yet verified; see [BUILD_STATUS.md](BUILD_STATUS.md). The backend was not present in this checkout when the frontend was built.

## Manual smoke check

See [frontend/tests/SMOKE.md](frontend/tests/SMOKE.md). Automated frontend tests check quote integrity, fixture conflicts, changed input, null values, bilingual numeric checks, urgent patterns, profile resets, preference feedback, and selected message content. These tests are distinct from the backend's held-out ML evaluation.
