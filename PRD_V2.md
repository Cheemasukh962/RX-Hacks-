# REXO v2: Product Requirements (redesign)

_Nov 15, 2026. Product PRD + design PRD combined. Supersedes the UI parts of PLAN.md. PLAN.md sections 5–6 (data + API contracts) still describe the existing backend. This file lists what is reused and what is new._

**Who this is for:** an agent building the new frontend (and Sukhman, for the new backend endpoints). Read sections 1–5 before writing code, and section 10 before building any screen. The backend lives in `backend/` (FastAPI). Every request/response shape is at `http://localhost:8000/docs` when it runs. The old frontend in `frontend/` is being replaced; reuse its API client ideas (`frontend/lib/api.ts`) but not its screens.

> **Current build focus: the meloxicam demo (section 11).** Build the frontend around that case first. The eye-drop case is the second example.

---

## 1. Problem

After a visit, patients take home an **after-visit summary (AVS)**. The clinician separately writes a **clinical note**. These two documents sometimes disagree (dose, how often, how long, continue vs. stop). Patients also often don't understand *what* a medicine does, its side effects, or *why* a missed dose matters.

From an eye doctor we spoke with: some patients don't grasp that skipping post-surgery steroid drops, even for a day, can risk losing their eyesight (e.g. corneal graft rejection). Antibiotics have the same problem: patients stop early or skip doses.

**REXO's job:** take the two documents, flag where they disagree, explain the plan in plain language, let the patient ask questions by voice, show *why* adherence matters, and help them write to their doctor. **It answers first and tries its best:** practical, sourced guidance on what a medicine does, how to take it, side effects, what to do about a missed dose, and what to watch for. Only when something is still unclear (the documents disagree, or the answer isn't in the documents or trusted references) does it say so and **offer** to email the doctor. The patient chooses; REXO never jumps to the email on its own. It never overrides the doctor's prescription: when documents disagree it explains both and what general guidance says, but the doctor decides which applies.

## 2. Users and modes

- **Patient** (primary), after a visit, on a phone or laptop. Needs English and Spanish.
- **Demo / judge mode:** synthetic document pairs with deliberate differences, so the conflict detection is visible.
- **Upload mode:** the user uploads their own AVS + clinical note (text or PDF). See the privacy note in section 7.

## 3. Core flow (the whole product)

```
[1] Input: AVS + clinical note
      ├─ Upload (PDF or paste text)            ← "real" path
      └─ Pick a synthetic demo pair            ← demo path (pairs are built to differ)
        │
        ▼
[2] Results page
      ├─ Plain-language SUMMARY (top)
      ├─ KEY ITEMS boxes: Medications · Follow-ups / tasks · Warning signs
      │     each box shows the source quote; disputed values are marked
      ├─ DIFFERENCES FLAGGED: each conflict shows BOTH quotes side by side
      │     └─ [Email my doctor] → AI drafts an email about this difference
      │            + patient adds own note (voice or text) → edit → send via their email app
      ├─ [Let's chat] ONE chat for the whole case (voice via Deepgram, or text)
      └─ per medication: [Why it matters] → illustrated risk cards (AI image + vetted caption)
```

## 4. Features

Status key: **✅ exists** (backend, tested) · **🟡 partial** · **🆕 new work**

### F1. Document input: 🟡
- Two slots: AVS and clinical note. Paste text ✅, upload `.txt` ✅, **upload PDF 🆕**.
- Demo pairs: `GET /api/demo-cases` → `POST /api/cases {demo_case_id}` ✅. There are 3 today: eye drops (frequency conflict), blood pressure (dose + continue-vs-avoid), and a matching control.
- **🆕 Antibiotic demo pair** (e.g. amoxicillin "10 days" in the AVS vs "7 days" in the note → `duration_mismatch`). The extractor already detects this live; it needs a fixture plus a `*.expected.json`.
- **🆕 PDF → text:** `POST /api/ingest/pdf` (multipart `file`) → `{text, pages, redacted_count, mode}`. Use a text-layer PDF library (e.g. `pypdf`). Scanned PDFs are out of scope, so say "paste the text instead".
- Then `POST /api/cases {documents: [{text, type_hint}]}` ✅ does redaction → OpenAI extraction → quote check → number check → conflict detection.

### F2. Difference detection: ✅
- Response `CarePlan.conflicts[]`: `{id, type: dose|frequency|action|date|duration _mismatch, instruction_ids[], level}`. Each instruction has `evidence: {document_id, quote}`, and every quote is verified to exist in the source text.
- **UI rule:** always show **both** quotes for a conflict. Never show one as "correct".

### F3. Summary + key items: 🟡
- Key items come straight from `CarePlan.instructions[]` (`kind`: medication / follow_up / lab / warning_sign / lifestyle / supply). Fields that are missing are `null`, so show "not in your documents", never a guess. ✅
- Per-item plain-language explanation: `POST /api/explain {case_id, profile_id, instruction_id}` ✅. It is live OpenAI wording, fact-checked against the quotes. **The UI must not display it if `fact_check.passed` is false.**
- **🆕 Case summary:** `POST /api/cases/{id}/summary {profile_id}` → `{summary, key_points[], citations[], mode}`. It is a short overview generated from the instructions only, with the same fact check as `/explain` (every number must come from a quote).

### F4. Email my doctor: 🟡
- Existing: `POST /api/briefing {case_id, profile_id, include: {concerns[], conflicts[]}}` → `{draft_en, draft_patient_language, citations}` ✅. It is template-based, includes both quotes per conflict, and never sends.
- **🆕 Extend for email:** add `patient_note` (text, or a voice transcript from `/voice/transcribe`) and return `{subject, body_en, body_patient_language}`. The AI may polish the wording, but quotes and numbers are inserted by code.
- **Sending:** a `mailto:` link or copy to clipboard, opened from the patient's own email app. **REXO never sends email itself** (it stays a patient click). The patient edits before sending.

### F5. Chat about the whole case (voice + text): 🆕 (biggest new piece)
- Today `POST /api/ask` ✅ only does keyword lookup and returns matching quotes, or "not in your documents".
- **🆕 `POST /api/chat`** `{case_id, profile_id, messages: [{role, content}]}` → `{answer, citations[], sources[], urgent, mode}`.
  - Context: both documents + extracted instructions + conflicts + profile (language, reading level).
  - Answers questions like: what does this medicine do, side effects, when/how to take it, what if I miss a dose.
  - **Grounding:** facts about *this patient's plan* come only from their documents (cite quotes). General drug facts (purpose, common side effects, missed-dose guidance) come from a **trusted reference**, not model memory: e.g. the openFDA drug label API (free, no key) or MedlinePlus. Label the answer "from your documents" vs "general drug information".
  - **Answer first, best effort.** The chat gives real, practical guidance: what the medicine is for, how and when to take it (from the documents), common and serious side effects, what to do if a dose is missed, food/alcohol/other-medicine interactions, and when to get help (from the trusted reference). It answers the question fully before suggesting anything else.
  - **Escalate only when unclear, and only as an offer.** If the documents disagree, the answer isn't in the documents or references, or the patient is still unsure after the answer, REXO says what is unclear and shows an **optional** `Email my doctor` button (or "ask your pharmacist"). It never opens the email flow automatically.
  - **Document conflicts:** explain what each document says and any relevant general guidance (e.g. "the label's usual maximum is once a day"). Then say the doctor needs to confirm which applies, and offer the email.
  - **Limits:** it never tells the patient to change their prescribed dose or schedule, or to stop or skip a prescribed medicine. Those changes are the doctor's call, and REXO says so plainly.
  - Urgent symptoms (existing `is_urgent` EN/ES) → "Call 911 or your care team now" and stop.
- **Voice in:** `POST /api/voice/transcribe` ✅ (multipart `audio` + `language` ∈ `en|es|multi`; Deepgram nova-3, handles Spanish/English mixing).
- **🆕 Voice out:** `POST /api/voice/speak {text, language}` → audio (OpenAI TTS `gpt-4o-mini-tts` works with our key; Deepgram Aura is an alternative). The browser `speechSynthesis` is an acceptable fallback.

### F6. "Why it matters" risk images: 🆕 (images, not video)
- A button per medication (and for antibiotics in general). It shows **2–4 illustrated cards** on what can happen if the medicine isn't taken as prescribed. Each card has one AI-generated illustration and a short caption.
  - Eye drops after a transplant: the eye needs the drops to calm inflammation → missed doses let inflammation build → that can risk rejection of the new tissue and vision → talk to your care team before changing anything.
  - Antibiotics: the medicine keeps working through the course → stopping early or skipping can let the infection come back → take it as prescribed and ask before stopping.
- `POST /api/risk-images {case_id, instruction_id, language}` → `{cards: [{caption, image_url, alt}], sources[], disclaimer, mode}`.
- **Captions come from vetted facts** (drug label / clinician-reviewed fact sheet for the demo medicines), written by code or the LLM from those facts only. **The image never carries text:** the caption is real HTML text (accessible, translatable, and image models misspell words).
- **Image style:** calm flat editorial illustration (warm neutrals + slate, simple shapes, a person or an eye/pill shown simply). **No** photorealism, injuries, gore, fear imagery, or a recognizable real person. Prompt template is in section 6.
- Every card set shows "Illustration, not a prediction for you" and ends with "Talk to your care team before stopping or changing any medicine."

### F7. "Show me your medicine" (camera): 🆕
- The patient holds a medicine bottle/box up to the camera. REXO reads the label, matches it to a medicine in **this case** (and its fact sheet), then **says out loud** what it is, what it's for (from the patient's documents), how they were told to take it, and key general info. The conversation continues in the chat (F5), with that medicine in focus. No typing or asking needed.
- **How (recommended):**
  - Browser `getUserMedia` → capture a still when the frame is steady. OpenCV, server-side or OpenCV.js, can pick a sharp, stable frame and crop/contrast-boost the label.
  - **Read the label with an OpenAI vision model** (image input). **OpenCV alone cannot read text**, and Tesseract OCR is the weaker fallback on curved bottle labels.
  - Fuzzy-match the read name (brand or generic, e.g. "Mobic" → meloxicam) against the case's `instructions[].medication_name` and the fact-sheet library.
- **Endpoint:** `POST /api/medicine/identify` (multipart `image`, `case_id`, `profile_id`) → `{medication_name, strength_seen, matched_instruction_id | null, confidence, spoken_summary, citations[], sources[], mode}`. Then `/voice/speak` reads `spoken_summary`.
- **Safety rules:**
  - **Confirm before talking:** "I see **Meloxicam 15 mg**. Is that right?" (one tap or a spoken "yes").
  - **Labels only, never loose pills:** we don't identify pills by shape or color.
  - **Not in the documents:** if the medicine isn't in the patient's documents, say so ("This isn't in your visit documents. Ask your pharmacist") and give only labeled general info.
  - **Strength doesn't match:** if the strength on the bottle differs from the documents, show it as a difference (amber) and offer "Email my doctor".

### Kept from v1 (backend exists; optional in the new UI)
- Teach-back check (`/api/teachback`): patient explains the plan in their own words → flags wrong dose/frequency. ML + rules.
- Barrier capture (`/api/barrier` + `/api/feedback`): "what's getting in the way" (cost, side effects, schedule…), using a classifier that learns from corrections.
- Personal learning: style bandit + term familiarity (`/api/profile`, `/api/feedback`). Evaluation page (`/api/eval`).
- **Decision needed:** keep teach-back/barriers in v2, or drop them for simplicity? They fit naturally *inside* the chat ("tell me how you'll take it").

## 5. Non-negotiable rules (all features)

1. Every fact about the patient's plan links to a quote from their documents. No quote → don't show it.
2. When documents disagree, show both quotes and explain them (plus relevant general guidance), but don't decide which one is the patient's instruction. Offer `Email my doctor` as an option.
3. **Answer first, escalate second.** REXO gives practical, sourced guidance and tries its best to resolve the question. Email/pharmacist is an *offered* next step when something stays unclear, never automatic. General drug info is labeled "General drug information" with its source. REXO never tells the patient to change, stop, skip or double a prescribed medicine.
4. AI may change wording, never numbers. Code checks numbers (`fact_check`). The UI hides anything that fails it.
5. Nothing is sent to a clinician without the patient clicking. Email goes through the patient's own email app.
6. Urgent symptom text (EN/ES) interrupts with "Call 911 or your care team now".
7. Every response carries `mode: "live" | "demo"`. Show "Demo mode" when live services aren't configured.
8. English + Spanish throughout. Original quotes stay in their original language.

## 6. Risk images: how to generate (researched Nov 15, 2026)

**Decision: images, not video.**
- OpenAI's video API (Sora 2) was shut down on Sept 24, 2026.
- Gemini video is asynchronous (tens of seconds to minutes) and needs a separate key.
- OpenAI **image** generation works with our existing credits.

- **Model:** OpenAI GPT-Image-2.5 **Flare** (OpenAI's "fastest model for high-quality, everyday image generation"). Sunburst is the higher-quality, slower option. `gpt-image-1` was shut down on Oct 23, 2026, so don't use it. **Confirm the exact model ID on OpenAI's models page before coding.** Cost is roughly a few cents per image.
- **Latency:** several seconds per image, so it is not instant. **Pre-generate and cache** the demo medicines (steroid eye drops, antibiotics, blood-pressure meds) × EN/ES at startup or in a script. Images are language-free (no text in the image), so one set serves both languages. Generate on click only for new medicines, with a skeleton loader. If generation fails or is refused, show the caption cards with a simple icon instead.
- **Cache key:** (medicine class, card index, style version). Store files under `backend/ml/artifacts/risk_images/` or a static folder. Never regenerate during the demo.
- **Prompt template** (per card):
  `Flat editorial illustration, calm and reassuring, warm ivory background, slate blue and soft sand palette, simple shapes, no text, no letters, no logos, no photorealism, no injury or blood. Scene: {scene from the vetted caption, e.g. "a person putting an eye drop in, a small calendar beside them"}.`
- **Safety review:** a person looks at every pre-generated image once before the demo. Discard anything inaccurate (wrong anatomy, wrong pill form) or alarming.

## 7. Open questions / risks

- **Real uploads = real health data.** v1 was synthetic-only. Uploading real documents sends them to OpenAI. For the hackathon: use real-*format* documents that are de-identified or used with consent, keep the redaction step, don't store anything server-side, and show a notice. Decide this before building upload.
- Chat drug facts: which trusted source (openFDA label vs. MedlinePlus vs. a small clinician-reviewed fact sheet for the demo meds)?
- Keep teach-back / barriers / learning profile in v2? (see section 4)
- Risk-image captions: who signs off on the vetted facts for the demo medicines (ideally the eye doctor we spoke with)?
- Brand: REXO keeps its own identity (section 10). Abridge's brand assets are reference only, not to be copied.

## 8. Acceptance (demo)

- [ ] Upload a PDF pair **and** pick a synthetic pair; both produce a care plan.
- [ ] Synthetic pairs show flagged differences with both quotes (eye drops: frequency; blood pressure: dose + continue/avoid; antibiotic: duration).
- [ ] Summary + key-item boxes show only document-backed facts; missing → "not in your documents".
- [ ] Email: AI draft + patient's voice/text note → editable → opens in the email app. Nothing auto-sends.
- [ ] Chat by voice: "What does prednisolone do?", "What if I miss a dose?", "Which dose is right?" → grounded answers, conflict routed to the care team, urgent text interrupts.
- [ ] "Why it matters" shows labeled, cached illustrated risk cards for the eye drops and an antibiotic instantly, with captions as real text.
- [ ] Meloxicam demo (section 11.6) runs end to end: real findings, demo-altered frequency difference → email, camera recognizes the bottle and speaks, voice chat, risk cards.
- [ ] Works at phone width, EN + ES.

## 9. Existing backend endpoints (all under `/api`)

`GET /health` · `GET /demo-cases` · `POST /cases` · `GET /cases/{id}` · `POST /profile` · `GET|PUT /profile/{id}` · `POST /profile/{id}/reset` · `POST /explain` · `POST /ask` · `POST /teachback` · `POST /barrier` · `POST /feedback` · `POST /briefing` · `POST /voice/transcribe` · `POST /ingest/photo` (501) · `GET /eval` · `POST /demo/reset`.
New in this PRD: `/ingest/pdf`, `/cases/{id}/summary`, `/chat`, `/voice/speak`, `/risk-images`, `/medicine/identify`, email fields on `/briefing`, within-document / only-in-one-document findings.

Run locally: `cd backend && uvicorn app.main:app --port 8000` (keys in `backend/.env`). Backend check: `python scripts/smoke_live.py`.

---

## 10. Design system (REXO visual identity)

_Adapted from a design PRD that documented Abridge's public brand (Pentagram, 2024). We keep its **principles** (precision + care, warm neutrals instead of clinical blue-and-white, one signal color used sparingly, display type only for big moments, firm calm motion, AA accessibility). We do **not** copy Abridge's brand assets: no "A"/bridge mark, no Abridge Display typeface, no signal-red palette, no "Taken care of" or other Abridge taglines, no split-letter waveforms or supergraphics. REXO is a different, patient-facing product and keeps its own identity._

### 10.1 Foundation
- **Name / mark:** "rexo." wordmark with the "+" mark (existing). One color only: ink, white, or slate on approved neutrals. No gradients, outlines or shadows.
- **Tagline:** "Your care, understood. Your concerns, heard." (existing)
- **Audience:** patients after a visit, often stressed, sometimes with limited health literacy or limited English. This is not a clinician tool, so the UI is calmer and simpler than a clinical product.
- **Principles:**
  1. **Source first.** Every fact sits next to the quote it came from. The quote card is our core visual unit.
  2. **Complexity into clarity.** Two dense documents in → one calm page out. Visual weight goes to "what do I do".
  3. **Human first, AI second.** Talk about the patient's care, not about the model. No "AI magic" language or visuals.
  4. **Confident, not cold.** Warm neutrals and plain words; never alarming, never cute about medicine.

### 10.2 Color tokens (contrast computed, WCAG 2.2)

| Token | Hex | Role |
|---|---|---|
| `ink` | `#1C2430` | Text, wordmark, dark surfaces |
| `stone-600` | `#5E5A55` | Secondary text |
| `slate-700` | `#34516D` | **Brand + primary actions** (buttons, links, focus ring) |
| `slate-500` | `#56718C` | Hover tints, secondary icons |
| `mist` | `#E0E7EE` | Info surfaces, assistant chat bubbles |
| `ivory` | `#F7F5F0` | Page background |
| `card` | `#FDFCF9` | Cards |
| `sand-200` | `#E8DCCB` | Warm surface for the summary band / brand moments |
| `amber-700` / `amber-50` | `#8A5A00` / `#FFF4DC` | **Documents disagree / needs clarification** |
| `danger-700` / `danger-50` | `#B42318` / `#FEF0EE` | **Urgent only** ("Call 911"), errors |
| `sage-700` / `sage-50` | `#2F6B4F` / `#E9F4EE` | Matches / done / success |

Verified pairs: ink on ivory 14.3:1 · ink on card 15.2:1 · slate-700 on ivory 7.6:1 · card on slate-700 8.0:1 · stone-600 on ivory 6.3:1 · slate-500 on ivory 4.7:1 · ink on mist 12.5:1 · slate-700 on mist 6.6:1 · amber-700 on amber-50 5.4:1 · danger-700 on danger-50 5.9:1 · card on danger-700 6.4:1 · sage-700 on sage-50 5.6:1. All pass AA for body text.

Rules:
- **C1 Ratio:** about 70% neutrals, 20% slate/mist, ≤10% semantic color. There is no decorative red.
- **C2 Semantic colors mean one thing each:** amber = documents disagree, red = urgent/error, sage = matches/done. Never decorative. **Color is never the only signal:** always pair it with an icon and a text label ("Needs clarification", "Get help now").
- **C3 Conflict ≠ danger:** a document difference is amber, not red. It is a question for the care team, not an emergency.
- **C4 Dark mode (optional):** base `#111821`, card `#1A2330`, text `#EDEBE6`, links slate lightened to `#8FB0CF`. Re-check contrast.

### 10.3 Typography
- **Display:** an open-source serif with character, e.g. **Fraunces** or **Source Serif 4** (Google Fonts). Use it for page headlines, the summary headline, and big numbers only, at **≥ 32px**, ≤ 8 words, sentence case. Never for paragraphs or UI labels.
- **Text / UI:** **Inter** (or Source Sans 3). Neutral, strong numerals, full Spanish support. Body **≥ 16px** (17–18px preferred for this audience), line-height 1.5.
- **Document quotes:** serif italic or a quiet mono so they read as "the original words", ≥ 15px.
- **Scale:** ratio 1.25 (16 · 20 · 25 · 31 · 39 · 49). Display leading 1.05–1.1. No all-caps except small letter-spaced eyebrow labels.

### 10.4 Core components (the visual language)
- **Quote card:** source label ("After-visit summary" / "Clinical note"), the exact quote, a link to view it in the document. Every medication, follow-up and answer shows one.
- **Difference card (signature element):** amber surface, "Your documents don't match", the two quote cards **side by side** (stacked on phone) with equal visual weight and **no "correct" marker**, then the action `Email my doctor`.
- **Summary band:** sand-200 band at the top of the results page with a display headline ("Here's your plan") and 3–5 plain bullets.
- **Key-item boxes:** three-up grid on desktop (Medications · Follow-ups & tasks · Warning signs), one column on phone. Each item shows name, amount, how often, how long, or "Not in your documents" in stone-600 italic. Never blank, never guessed.
- **Chat panel:** one conversation for the whole case. Large mic button (≥ 56px) as the primary input, text box secondary. The assistant bubble is mist, the patient bubble is card with a slate border. Each answer is tagged "From your documents" (with quote cards) or "General drug information" (with source name). Conflicts in answers render a mini difference card.
- **Recording state:** simple animated level bars in slate while listening, a "Listening…" label and a stop button. The live transcript appears as it comes.
- **Risk cards:** illustration on top (no text in the image), caption below as real text, "Illustration, not a prediction for you" footer. 2–4 cards, horizontal scroller on phone.
- **Email composer:** editable subject + body, a "Your note" field with mic, quotes inserted as blockquotes, `Open in email app` (mailto) + `Copy`. No send button.
- **Status chips:** `Demo mode` (sand) vs `Connected` (sage). The synthetic banner "Synthetic demo record, not a real patient" is shown on demo cases.
- **Urgent interrupt:** full-width danger panel with "Get help now · Call 911 or your care team now". It pauses the flow and can't be dismissed by accident.

### 10.5 Imagery
- **Primary imagery is the product itself:** quote cards, difference cards, the plan.
- **Illustrations** (risk cards, empty states, onboarding): flat editorial style, warm ivory/sand/slate palette, simple people and objects, no text in images.
- **Avoid:** stock "doctor with stethoscope" photos, blue-tinted hospital imagery, holographic UIs, robots, glowing brains, AI particle networks, anything graphic or fear-based.

### 10.6 Motion
- **Signature, "separate & settle":** when a difference is shown, the two quote cards slide apart from one stack into side-by-side positions and settle. It plays once per difference card, on first view.
- **Easing:** firm ease-out, 200–300ms for UI, ≤ 600ms for the signature moment. No bouncy springs and no looping decoration.
- **Loading:** skeleton cards in the shape of the result (not spinners). Extraction takes ~10s, so show progress steps ("Reading your documents → Checking quotes → Comparing").
- **`prefers-reduced-motion`:** no movement; show the final state.

### 10.7 Layout and screens
- **Phone first** (390px). 16px side gutter, tap targets ≥ 44px, one primary action per section, generous vertical rhythm.
- **Screens:**
  1. **Start:** headline + two paths: `Upload my documents` and `Try a sample` (sample cards: eye drops after surgery, blood pressure, antibiotic, matching control).
  2. **Upload:** two drop zones (AVS, clinical note) accepting PDF or pasted text, a "fictional or consented documents only" checkbox, and a redaction count.
  3. **Results:** summary band → difference cards (if any) → key-item boxes → `Let's chat` (sticky on phone) → per-medication `Why it matters`.
  4. **Chat:** full-screen on phone, side panel on desktop.
  5. **Email composer:** full-screen sheet / modal.
  6. **Risk cards:** sheet over the results page.
- **Language toggle** EN/ES always in the header. Original quotes stay in their source language with an "(original, in English)" label.

### 10.8 Voice and copy
About a 6th-grade reading level, short sentences, second person ("your documents say…").

| We are | We are not |
|---|---|
| Clear: "Your documents don't match on how often." | Jargon: "Frequency discrepancy detected" |
| Helpful first: "Meloxicam is a pain and anti-inflammatory medicine. Take it with food to protect your stomach." | Deflecting: "Ask your doctor." as the whole answer |
| Calm and caring: "This part is unclear. Want me to draft an email to your doctor?" | Alarming: "Danger! Wrong dose!" |
| Honest: "This isn't in your documents." | Guessing or reassuring: "That's probably fine." |
| Sourced: "From your after-visit summary: …" | Vague "AI magic" claims |
| Patient-led: "You decide what to send." | Automatic: "We emailed your doctor." |

CTA vocabulary stays plain: `Upload documents`, `Try a sample`, `Let's chat`, `Email my doctor`, `Why it matters`, `Open in email app`, `Copy`.

### 10.9 Accessibility
- WCAG 2.2 AA minimum (pairs in 10.2). A visible 2px slate focus ring on every interactive element.
- Display type never carries essential information alone. Every image has alt text, and the risk-card meaning lives in the caption text.
- Voice is never required: every voice action has a text equivalent, and a denied mic shows "You can type instead".
- Test Spanish (longer strings) at phone width. Respect `prefers-reduced-motion`.

---

## 11. Main demo: the meloxicam case (current build focus)

### 11.1 Source documents
- **Real records from a team member, used with his consent:** one office visit for chronic low back pain (exported from a patient portal as PDFs). There are two documents:
  - **After-visit summary (AVS):** the patient-facing summary.
  - **Clinical note:** the doctor's progress note.
- **The PDFs are NOT in git** (`*.pdf` is gitignored). They live only on the presenter's machine. Never commit them, the extracted text, or screenshots containing identifiers.
- **Before anything goes to OpenAI or on screen,** a prepared **demo copy** removes:
  - patient name, date of birth, MRN, CEID
  - the physician's and PT therapists' names
  - addresses and phone numbers
  - **the full "Current Problem List"** (unrelated, sensitive diagnoses that add nothing to the demo)

  Keep that demo copy in a gitignored `private/` folder. The app's redaction step stays on as a second layer, but the demo copy is the main protection.

### 11.2 What the real documents contain (relevant parts)

| | After-visit summary | Clinical note |
|---|---|---|
| Meloxicam | 15 mg tab, "Take 1 tablet by mouth daily. Take with food" | "Take meloxicam." (no dose) |
| Prednisone | 10 mg tab, 10-day taper (5→4→3→2→1 tablets, 2 days each, then stop) | "Can also try steroid taper, but doubt radiculitis." |
| Cyclobenzaprine | 10 mg, "1 tablet by mouth 2 times a day as needed for muscle spasms". **Also shown as "Status: Discontinued"** at the top of the same AVS | Listed under relevant medications; not in the plan |
| Given in clinic | ketorolac (Toradol) | "IM Toradol at the time of the visit" |
| Follow-up | Two physical-therapy visits | "reStart physical therapy" |
| Imaging | not mentioned | "get new x-ray to rule out compression fracture" |
| Warning sign | not mentioned | "go to ER if symptoms of cauda equina syndrome develop" |

**Real findings REXO should surface, even before we change anything:**
1. **Cyclobenzaprine is marked both "Discontinued" and "START taking"** in the AVS. Flag it as a difference *within one document* (it needs a small backend addition, since today's conflicts compare AVS vs. note).
2. **The ER warning sign is only in the note:** "Your after-visit summary doesn't mention this. Your clinical note says: go to the ER if symptoms of cauda equina syndrome develop." Plain-language definition via the glossary.
3. **The X-ray order is only in the note:** it shows as a follow-up task with the note's quote.
4. **The prednisone wording differs:** the note says "can also try", the AVS gives a full taper. Show it as "worded differently, ask your care team", not as a numeric conflict.

### 11.3 Demo-altered version (to show the email flow)
- We make an **altered copy of the clinical note**, clearly labeled `DEMO-ALTERED` in the UI and in the file name. It changes one line so it creates a clear, numeric difference:
  - **Recommended:** note plan says **"Take meloxicam 15 mg twice daily"** vs. the AVS "1 tablet daily". That's a `frequency_mismatch`.
  - It is a realistic and important catch: twice daily would double the daily amount.
  - REXO shows both quotes, does not pick one, and offers **Email my doctor**.
- Optional second alteration: the note says "Stop cyclobenzaprine". That's an `action_mismatch` with the AVS's "as needed".
- The app shows a toggle: **Original documents** ↔ **Demo-altered**. That way judges see both the real findings and the email flow, and nobody mistakes the altered text for the real record.

### 11.4 Optional third source: visit transcript (synthetic)
- A short **synthetic** doctor–patient conversation consistent with the original note. Example: the doctor explains meloxicam once a day with food, and to stop and call for black stools or stomach pain. It is generated once, reviewed by a person, and saved as text (optionally also as audio via TTS).
- Shown as a third source ("What your doctor said"), with quotes like the other documents.
- **Contract change:** a new document type `visit_transcript` (currently only `after_visit_summary | clinical_note`). Treat this as a stretch goal and include it only if time allows.

### 11.5 Meloxicam fact sheet (for chat, camera, and risk images)
A vetted file, e.g. `backend/app/drug_facts/meloxicam.json`, built from the **FDA drug label** (openFDA) and **MedlinePlus**. Each fact has its source and URL.

- **What it is:** an NSAID for pain and inflammation (arthritis, back pain as prescribed).
- **How to take it** (general, the documents win for this patient): once daily, with food.
- **Boxed warnings on the label:** risk of heart attack/stroke, and stomach/intestinal bleeding, ulcers or perforation.
- **Interactions to ask about:** other NSAIDs (ibuprofen, naproxen; also ketorolac/Toradol), corticosteroids like prednisone (higher stomach-bleeding risk), blood thinners, some blood-pressure medicines. **Note for the demo chat:** this patient's own plan included prednisone, so "Can I take meloxicam with prednisone?" is a good question. The answer explains what the label says about combining them (higher stomach-bleeding risk, ways to lower it such as taking it with food, signs to watch for) and notes that their doctor prescribed both. If the patient is still unsure, it offers to email the doctor or suggests asking the pharmacist.
- **When to get help** (from the label): black or bloody stools, vomiting blood, chest pain, shortness of breath, weakness on one side, slurred speech.
- **Risk-image cards (F6):**
  1. Taking it with food protects the stomach.
  2. Doubling up or adding other pain relievers like ibuprofen raises stomach-bleeding risk.
  3. Warning signs to act on right away.
  4. "Ask your care team before stopping or changing."

### 11.6 Demo script (≈3 min)
1. **Upload** the two PDFs (demo copies) → extraction runs → **summary + key items**: meloxicam, prednisone taper, cyclobenzaprine, PT visits, X-ray, warning sign.
2. **Real findings:** "Discontinued vs. START" for cyclobenzaprine; the ER warning and X-ray found only in the note.
3. **Toggle to Demo-altered** → the **meloxicam frequency difference** appears with both quotes → **Email my doctor** → the patient adds a spoken note ("I've been taking it once a day, which is right?") → editable email → opens in the email app.
4. **Hold up the real meloxicam bottle** to the camera → "I see Meloxicam 15 mg. Is that right?" → yes → REXO **says out loud** what it is, how the documents say to take it (once daily with food), and the main warnings.
5. **Voice chat:** "What happens if I take it on an empty stomach?" / "Can I take ibuprofen with it?" → REXO answers directly from the label (labeled, sourced). Only if the patient is still unsure does it offer "Email my doctor".
6. **Why it matters** → meloxicam risk cards.
7. (Optional) Switch to the **eye-drop case** for the "skipping a day can risk your eyesight" story. Daily drops such as post-transplant steroids or glaucoma drops are the stakes example.

### 11.7 Backend work this demo needs (priority order)
1. `POST /api/ingest/pdf` (text-layer PDFs; these portal exports have a text layer) + **redaction tuned for portal exports** (member name, DOB, MRN, CEID, clinician names, addresses, phones), plus the demo-copy prep.
2. Extraction prompt check on this format: the medication table, the multi-step taper, "as needed", and "Status: Discontinued".
3. **Within-document contradiction** check (Discontinued vs. START) and **"only in one document"** findings (warning signs, orders) as a new finding type alongside `conflicts`.
4. Meloxicam fact sheet + `/api/chat` grounded on documents + fact sheet.
5. `/api/medicine/identify` (camera) + `/api/voice/speak`.
6. Email fields on `/briefing`.
7. Risk images for meloxicam (pre-generated, reviewed).
8. Stretch: the synthetic transcript as a third source.
