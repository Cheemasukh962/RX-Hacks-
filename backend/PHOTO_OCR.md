# Bottle-label OCR

`POST /api/ingest/photo`, multipart field `image`, now runs local OpenCV and Tesseract. JPEG, PNG and WebP only; maximum 8 MB and 24 megapixels. EXIF orientation is applied and metadata is not returned.

Install Python dependencies from `requirements.txt`, then install the **system OCR binary**:

```sh
# macOS
brew install tesseract
# Debian/Ubuntu
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-eng
```

Restart FastAPI after installing. No AI key is needed for OCR. It currently reads English labels only. Existing English/Spanish UI support does not imply Spanish OCR support.

For Render, the current Python-only `render.yaml` does not install OS packages. Use a Docker service with Root Directory `backend` and its included `Dockerfile`, or supply Tesseract through your hosting image. This Dockerfile has not been deployed/tested here. Do not assume `pip install pytesseract` installs Tesseract.

Pipeline: validate/decode → EXIF transpose → full-frame OCR plus yellow-label crop when detected → grayscale/CLAHE and small rotations → Tesseract block/sparse passes → conservative text-field extraction → preserve disagreeing candidates → editable patient review. A blue cap or orange bottle never determines a medicine name. It does not perform cylindrical unwrapping or read the hidden side; use separate front/back photos.

Recognized fields: printed medicine name beside strength, dosage form, `Generic for` brand text, numeric directions, food instructions, quantity, refills and discard-after text. OCR candidates can contain errors: dates, decimals and curved text require particular care. No fuzzy drug-name correction, catalog lookup, identity assertion, treatment decision, refill estimate or schedule is inferred. Missing fields are absent, not invented. Confidence is an OCR engine score, not a probability that the medication is correct.

The original five response fields remain. Optional `fields`, `conflicting_fields`, `warnings`, `requires_review`, `engine`, and `privacy` are documented in PLAN.md. Evidence quotes are exact **OCR fragments**, not verified readings of the physical label. `mode: live` means real local OCR ran, not that a clinician or external AI verified anything.

Privacy: server memory and Tesseract's short-lived temporary files are used; uploads and OCR are not stored by app code or sent to third-party AI. Only supported medication fragments are returned, and the preview is newly rendered from those fragments. Other lines are omitted. `redacted_count` is a count of omitted OCR lines across passes, not guaranteed identifiers removed. This is not a privacy-compliance or complete de-identification claim. Never commit reference bottle photos, patient names, Rx numbers or original previews. The frontend requires synthetic-data confirmation before importing text into the care-plan flow.

Verification:

```sh
python -m pytest -q tests/test_vision.py
```

Tests generate synthetic yellow labels in memory, including the reference medicine/strength pattern, back-label fields, and a small rotation. They check actual OCR, malformed images, size limits, omission of identifiers, preserved evidence, missing data, retained candidates, and HTTP behavior. Personal reference images from chat were visually available but not mounted as local files; these exact photos have **not** been run through the pipeline. Accuracy on real-world curved labels remains unmeasured.

Frontend: Documents → Read a medicine bottle → choose front photo → add back photo → compare every candidate to label → edit combined text → confirm synthetic text → import. No care plan is created automatically.

References used for preprocessing: [Tesseract image quality and page segmentation](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [OpenCV image transformations](https://docs.opencv.org/doc/doxygen/html/d7/d1b/group__imgproc__misc.html).

## Camera medicine endpoints

`POST /api/medicine/identify` accepts multipart `image`, `language`, optional `case_id` and `profile_id`. It reuses OCR and adds the proposed brief fields (`found`, `medication_name`, `strength_seen`, `confidence`, `text_seen`, `matched_instruction_id`, `confirm_prompt`) plus candidate/strength-difference evidence. Meloxicam/Mobic must match an exact OCR keyword; unknown names are not silently fuzzy-corrected. This implementation uses Tesseract instead of DB/CRNN weights.

The camera button explicitly requests permission. A capture reads up to three consecutive frames, requiring two agreeing name/strength candidates before offering confirmation. Equal-strength votes withhold a result; a uniquely dominant reading with at least two OCR-pass votes can be offered, while all candidates remain available in photo review. Tracks stop after a match, on Stop camera, and on leaving the screen. The 3-second/9-of-10 physical-bottle target is **not measured or claimed**.

`POST /api/medicine/intro` accepts `{medication_name: "meloxicam", confirmed: true, case_id?, language?}`. It refuses unconfirmed requests, reads only current document quotes, and states when medicine is absent or instructions conflict. Browser read-aloud is offered only after confirmation. The meloxicam fact sheet is DRAFT, so general facts/narration stay disabled pending human review. `/medicine/chat`, external vision fallback, automatic voice loop, and `/voice/speak` are not implemented in this computer-vision slice. Existing Deepgram transcription remains available elsewhere.
