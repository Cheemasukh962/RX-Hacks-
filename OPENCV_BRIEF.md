# OpenCV branch: "Show me your medicine"

**Branch:** `open-cv` (from `main`). **Owner:** Amrit. **Read with:** `PRD_V2.md` section 4 (F5 chat, F7 camera) and section 11 (meloxicam demo).

## 1. What to build (one sentence)

The patient holds up their **meloxicam** bottle to the camera. REXO reads **"MELOXICAM"** on the label, says *"This looks like Meloxicam 15 mg. Would you like to learn more?"*, and if they say yes, starts a **voice conversation** (Deepgram listens, OpenAI answers, REXO speaks), using facts we prepared ahead of time.

## 2. Demo flow

```
camera on (browser getUserMedia)
   │  every ~500 ms send a frame (or only when the image is steady)
   ▼
POST /api/medicine/identify  (OpenCV: find text → read text → match "meloxicam"/"mobic")
   │  no match → keep scanning ("Hold the label toward the camera")
   ▼  match
"I see Meloxicam 15 mg. Is that right?"        ← confirm first (tap or say "yes")
   ▼  yes
spoken intro (from the fact sheet + the patient's documents, if a case is loaded)
"Would you like to learn more?"
   ▼  yes
voice chat loop:  mic → /api/voice/transcribe (Deepgram) → /api/medicine/chat (OpenAI + fact sheet)
                  → /api/voice/speak (OpenAI TTS) → play audio → listen again
```

## 3. What already exists (use it, don't rebuild it)

| Need | Where |
|---|---|
| Speech → text | `POST /api/voice/transcribe` (multipart `audio` + `language` = `en`/`es`/`multi`), Deepgram nova-3. In `backend/app/main.py`. |
| OpenAI JSON calls | `backend/app/llm.py` → `chat_json(system, user, schema)`. Returns `None` on any failure, so always have a fallback. |
| Urgent-symptom check (EN/ES) | `backend/app/safety.py` → `is_urgent(text)`, `urgent_message(lang)`. Run it on every user message. |
| Number fact check | `safety.fact_check(text, sources)`: every number in the answer must appear in a source. |
| Patient's documents (optional) | If a `case_id` is passed: `store.get_case(case_id)` → `instructions[]` (find `medication_name == "meloxicam"`; its `evidence.quote` is the patient's own instruction). |
| **Prepared drug facts** | **`backend/app/drug_facts/meloxicam.json`**: what it does, uses, how to take, max dose, missed dose, boxed warnings, side effects, get-help-now signs, interactions, alcohol, pregnancy, in EN + ES, each with a source URL. **It is a DRAFT: someone must check it against the label before the demo.** |
| Keys | `backend/.env` (`OPENAI_API_KEY`, `DEEPGRAM_API_KEY`). Never commit it. |

## 4. Recognizing the bottle with OpenCV

OpenCV **can** read text, via its `dnn` module ([tutorial](https://docs.opencv.org/4.13.0/d4/d43/tutorial_dnn_text_spotting.html)):

1. **Grab a good frame:** reject blurry frames (variance of Laplacian below a threshold), convert to grayscale, boost contrast (CLAHE).
2. **Find text regions:** `cv2.dnn.TextDetectionModel_DB` with a pretrained DB model (the tutorial links the weights; input ~736×736, binary threshold 0.3, polygon threshold 0.5, unclip ratio 2.0).
3. **Read each region:** `cv2.dnn.TextRecognitionModel` with a CRNN ONNX model + its alphabet file, `setDecodeType("CTC-greedy")`. Crop each detected box (perspective-warp the rotated rectangle) and `recognize()` it.
4. **Match:** lowercase the words and fuzzy-match against `match_keywords` in the fact sheet (`meloxicam`, `mobic`). Use `difflib.get_close_matches(word, keywords, cutoff=0.75)` so "MEL0XICAM" or "meloxicarn" still match. Also look for a strength like `15 mg` / `7.5 mg` with a regex.
5. **Require 2–3 matching frames in a row** before announcing, so a single misread doesn't trigger it.

**Fallback if OpenCV OCR struggles** (curved labels, glare): send the best frame to an OpenAI vision model and ask for `{medication_name, strength}` as JSON. Keep OpenCV for the frame selection and cropping. Ship whichever works reliably on the real bottle; reliability matters more than purity for the demo.

**Put model files in** `backend/ml/.cache/ocr/` (already gitignored). Add a small download script rather than committing weights. Add `opencv-python-headless` (or `opencv-contrib-python-headless` if a class is missing) to `backend/requirements.txt`.

## 5. Endpoints to add (proposed shapes)

```
POST /api/medicine/identify        multipart: image, language (en|es), case_id? , profile_id?
→ { found: bool, medication_name: "meloxicam" | null, strength_seen: "15 mg" | null,
    confidence: 0..1, text_seen: [str], matched_instruction_id: str | null,
    confirm_prompt: "I see Meloxicam 15 mg. Is that right?", mode }

POST /api/medicine/intro           { medication_name, language, case_id?, profile_id? }
→ { spoken_text, citations[] (document quotes), sources[] ({title,url}), mode }

POST /api/medicine/chat            { medication_name, language, case_id?, messages:[{role,content}] }
→ { answer, tier: "documents" | "drug_reference" | "web", citations[], sources[], offer_email: bool, urgent, mode }

POST /api/voice/speak              { text, language }  → audio/mpeg (OpenAI TTS, e.g. gpt-4o-mini-tts)
```

`/medicine/chat` is the first slice of the PRD's `/api/chat` (F5). Build it so it can be generalized to the whole case later.

## 6. How the conversation answers (from PRD F5)

1. **Patient's documents first.** If a case is loaded, the dose/schedule comes from their documents, e.g. "Your after-visit summary says: take 1 tablet by mouth daily, take with food." The documents win over everything.
2. **Then the fact sheet.** Answer from `meloxicam.json`, labeled "General drug information" with its source.
3. **Then the web.** If neither covers it, use the OpenAI Responses API `web_search` tool, prefer FDA/MedlinePlus/NIH/Mayo/Cleveland Clinic/NHS, and return the clickable `url_citation` links. Send only the medicine name + question, never patient details.
4. **Answer first, best effort.** Give a real, practical answer. Offer "Email my doctor" or "ask your pharmacist" (`offer_email: true`) only when something is still unclear. Never open the email automatically.
5. **Limits:** never tell them to change, stop, skip or double a prescribed dose. That's the doctor's call, and say so plainly. Run `is_urgent()` on every message; if it's urgent, answer only with `urgent_message()`.
6. **Numbers:** run `fact_check(answer, [fact sheet text + document quotes])`. If it fails, fall back to reading the fact-sheet text directly.

## 7. Safety rules for the camera

- **Confirm before talking:** never start explaining until the patient says or taps "yes".
- **Labels only:** never identify loose pills by shape or color.
- **Unknown medicine:** if there is no fact sheet, say "I can't read that label clearly" or "I don't have information on this one yet", offer typing, and don't guess.
- **Strength mismatch:** if the bottle says 7.5 mg but the documents say 15 mg, say so plainly ("Your bottle says 7.5 mg, but your after-visit summary says 15 mg") and offer to email the doctor.
- **Privacy:** process frames in memory only. Don't save camera images to disk or logs. The camera only turns on when the patient presses a button, and it shows a visible "camera on" state.

## 8. Done when

- [ ] Holding the real meloxicam bottle at ~30–50 cm in normal room light is recognized within ~3 s, 9 times out of 10.
- [ ] Other objects or text don't trigger a match (try 10 random labels and boxes).
- [ ] Confirm → spoken intro → "learn more?" → three spoken questions answered from the fact sheet: "What does it do?", "What are the side effects?", "What if I miss a dose?".
- [ ] A question not in the fact sheet (e.g. "Can I play basketball while taking it?") → web answer with source links.
- [ ] "I have black stools and chest pain" → urgent message only.
- [ ] Works in Spanish (`language: "es"`, Deepgram `multi`).
- [ ] `cd backend && python -m pytest -q` still passes. Add tests for keyword matching (pure function, no camera) and for the chat's urgent and limits behavior with the LLM disabled.
- [ ] Fact sheet reviewed by a person (`status: REVIEWED`).

## 9. Out of scope for this branch

Other medicines (add fact sheets later with the same JSON shape), PDF upload, email drafting, risk images. Those are on other branches/PRD items.

## 10. Run it

```bash
cd backend
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs
python -m pytest -q
```

## Implementation handoff (Amrit, open-cv)

Implemented the computer-vision slice with local OpenCV preprocessing + Tesseract (rather than DB/CRNN weights). Includes photo review, camera capture with two agreeing frames, exact meloxicam/Mobic label matching, competing OCR candidates, case instruction matching, strength-difference evidence, and a confirmation-gated document intro with browser read-aloud. No images go to external AI.

The prepared fact sheet remains DRAFT. General-info narration, `/medicine/chat`, web search, automatic voice conversation, and `/voice/speak` are not part of this slice. These need reviewed facts and coordination with the chat backend. The exact personal reference photos are not present as local files, so the 3-second/9-of-10 real-bottle target remains unverified. See `backend/PHOTO_OCR.md` for setup, OS dependency, tests, contracts, and limitations. Do not mark the full checklist done from synthetic OCR tests.
