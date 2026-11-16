"""Local bottle-label OCR. No image/text is sent to an external service or persisted.

This reads printed label text, not a medicine's identity from its appearance.
All values are unverified transcription candidates requiring human review.
"""
from __future__ import annotations

import base64
import io
import re
import warnings
import time
import threading
from collections import defaultdict

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

def _configure_tesseract() -> None:
    """Use TESSERACT_CMD if set; else, on Windows, the standard installer path when it isn't on PATH."""
    import os
    import shutil
    cmd = os.getenv("TESSERACT_CMD")
    if not cmd and not shutil.which("tesseract"):
        for candidate in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
            if os.path.exists(candidate):
                cmd = candidate
                break
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


_configure_tesseract()

_OCR_LOCK = threading.BoundedSemaphore(2)
MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 24_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class VisionError(ValueError):
    pass


def decode_image(payload: bytes) -> np.ndarray:
    if not payload or len(payload) > MAX_BYTES:
        raise VisionError('Choose a JPEG, PNG, or WebP image under 8 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as image:
                # Some phone .jpg files use the MPO JPEG container. Read its first image.
                if image.format not in ('JPEG', 'MPO', 'PNG', 'WEBP'):
                    raise VisionError(f'Detected {image.format or "unknown"} image data. Export as JPEG, PNG, or WebP; renaming the extension does not convert the image.')
                if image.width * image.height > MAX_PIXELS or min(image.size) < 120:
                    raise VisionError('The image is too large or too small. Use a clear close-up under 24 megapixels.')
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((2200, 2200))
                return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise VisionError('The image could not be decoded. Try a clear JPEG or PNG.') from exc


def image_variants(image: np.ndarray):
    """Full frame plus a yellow-label crop; never assume a cap color identifies medicine."""
    frames = [image]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([12, 65, 90]), np.array([42, 255, 255]))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
        if w * h > image.shape[0] * image.shape[1] * .04 and h > 80 and w > 100:
            margin = max(15, int(w * .06))
            frames.append(image[max(0, y-margin):min(image.shape[0], y+h+margin), max(0, x-margin):min(image.shape[1], x+w+margin)])
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = min(2.0, 1800 / max(gray.shape))
        if scale > 1:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        # Small rotations help sloping labels; cylindrical wrapping still needs another photo.
        yield gray, 6
        yield contrast, 11
        if len(frames) > 1 and frame is frames[-1]:
            for angle in (-7, 7):
                matrix = cv2.getRotationMatrix2D((gray.shape[1]/2, gray.shape[0]/2), angle, 1)
                yield cv2.warpAffine(gray, matrix, (gray.shape[1], gray.shape[0]), borderValue=255), 6


def ocr_lines(image: np.ndarray) -> list[dict]:
    lines = []
    deadline = time.monotonic() + 20
    try:
        for variant, psm in image_variants(image):
            remaining = deadline - time.monotonic()
            if remaining < 1:
                break
            data = pytesseract.image_to_data(variant, lang='eng', config=f'--psm {psm}', output_type=pytesseract.Output.DICT, timeout=min(5, remaining))
            grouped = defaultdict(list)
            for i, word in enumerate(data['text']):
                if word.strip() and float(data['conf'][i]) >= 0:
                    grouped[(data['block_num'][i], data['par_num'][i], data['line_num'][i])].append((word.strip(), float(data['conf'][i])))
            for words in grouped.values():
                lines.append({'text': ' '.join(word for word, _ in words), 'ocr_confidence': round(sum(conf for _, conf in words) / (100 * len(words)), 3)})
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError('Local OCR is not installed on this server. Please type the label text instead.') from exc
    except RuntimeError as exc:
        raise VisionError('OCR took too long. Crop closer to the label and try again.') from exc
    return lines


_STRENGTH = r'\d+(?:\.\d+)?\s*(?:mcg|mg|g|ml|%)\b'
_MEDICINE = re.compile(rf'^([A-Za-z][A-Za-z -]{{2,65}}?)\s+({_STRENGTH})(?:\s+((?:TABLETS?|CAPSULES?|DROPS?|SUSPENSION|SOLUTION|CREAM|OINTMENT)\b))?', re.I)
_IDENTIFIER = re.compile(r'\b(?:rx\s*[#:]|patient|dob|mrn|claim|phone|www\.|https?://)\b|\d{3}[-.) ]\s*\d{3}[- ]\d{4}', re.I)


def extract_label_fields(lines: list[dict]) -> tuple[list[dict], list[str], int]:
    """Only return medication-related fragments; names/Rx numbers/addresses never leave OCR."""
    fields, safe_lines = [], []
    seen = {}
    omitted = 0

    def add(field, value, quote, confidence):
        key = (field, value.casefold())
        if key in seen:
            seen[key]['supporting_passes'] += 1
            return
        fields.append({'field': field, 'value': value, 'evidence': {'document_id': 'bottle-label', 'quote': quote}, 'ocr_confidence': confidence, 'status': 'needs_review', 'supporting_passes': 1})
        seen[key] = fields[-1]
        if quote not in safe_lines:
            safe_lines.append(quote)

    for line in lines:
        text, confidence = line['text'].strip(), line.get('ocr_confidence', 0)
        if _IDENTIFIER.search(text):
            omitted += 1
            continue
        matched = False
        medicine = _MEDICINE.search(text)
        known = re.search(r'\b(meloxicam|mobic)\s*(\d+(?:\.\d+)?\s*mg)\b(?:\s+(tablets?|capsules?))?', text, re.I)
        if known:
            medicine = known
        if medicine and not re.match(r'^(take|use|qty|quantity|refills|generic|discard|expires|mfr)\b', medicine[1], re.I):
            # Restrict evidence to the recognized fragment, not the whole line (which may include a name).
            quote = medicine[0].strip()
            add('medication_name', medicine[1].strip(), quote, confidence)
            add('strength', medicine[2].strip(), quote, confidence)
            if medicine[3]:
                add('dosage_form', medicine[3].strip(), quote, confidence)
            matched = True
        patterns = [
            ('brand', r'generic for\s*:\s*([A-Za-z][A-Za-z -]{1,35})'),
            ('directions', r'\b(?:take|use|apply|instill)\s+\d+(?:\.\d+)?\s*(?:tablets?|capsules?|drops?|puffs?|ml|mg)\b(?:\s+(?:by mouth|orally|in (?:the )?(?:right|left|operated) eye|once|twice|three times|four times|daily|a day|per day|every \d+ hours?|as needed|with food|for \d+ days?)){0,8}'),
            ('food_instruction', r'\b(?:take|may take) with food\b(?: to lessen chance of stomach upset)?'),
            ('quantity', r'\b(?:qty|quantity)\s*[:.]\s*(\d+\s*(?:tabs?|tablets?|capsules?|caps?|ml)?)'),
            ('refills', r'\brefills?\s*[:.]\s*(\d+)'),
            ('discard_after', r'\b(?:discard after|expires?|expiration)\s*[:.]\s*([0-9A-Za-z/-]{6,18})'),
        ]
        for field, pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                quote = match[0].strip()
                add(field, (match[1] if match.lastindex else quote).strip(), quote, confidence)
                matched = True
        if not matched:
            omitted += 1
    return fields, safe_lines, omitted


def safe_preview(lines: list[str]) -> str:
    """A text-only review image, never an unredacted thumbnail of the original bottle."""
    canvas = Image.new('RGB', (900, max(150, 45 * (len(lines) + 2))), '#f7f5f0')
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 15), 'OCR TRANSCRIPTION - VERIFY AGAINST THE ORIGINAL LABEL', fill='#34516d')
    for i, line in enumerate(lines):
        draw.text((20, 65 + i * 40), line.encode('ascii', 'replace').decode('ascii')[:120], fill='#243a50')
    output = io.BytesIO()
    canvas.save(output, format='PNG')
    return base64.b64encode(output.getvalue()).decode()


def recognize_bottle(payload: bytes) -> dict:
    if not _OCR_LOCK.acquire(blocking=False):
        raise RuntimeError('The OCR reader is busy. Please try again in a moment.')
    try:
        return _recognize_bottle(payload)
    finally:
        _OCR_LOCK.release()


def _recognize_bottle(payload: bytes) -> dict:
    image = decode_image(payload)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if sharpness < 18:
        raise VisionError('The label is too blurry or has no readable detail. Hold still, move closer, and try again.')
    fields, safe_lines, omitted = extract_label_fields(ocr_lines(image))
    grouped = defaultdict(set)
    for field in fields:
        grouped[field['field']].add(field['value'].casefold())
    conflicts = [key for key, values in grouped.items() if len(values) > 1]
    warnings_out = ['Unverified OCR transcription. Check every field against the physical label before using it.', 'This reads printed text; it does not verify the bottle contents or recommend treatment.', 'Curved, covered, or cropped text may be missing. Photograph the front and back separately.']
    if not any(field['field'] == 'medication_name' for field in fields):
        warnings_out.append('No medicine name and strength could be read together. Retake a closer, front-facing photo.')
    if conflicts:
        warnings_out.append('OCR passes disagree. All candidates are retained; no value was selected automatically.')
    return {'mode': 'live', 'text': '\n'.join(safe_lines), 'redacted_count': omitted, 'preview_png_b64': safe_preview(safe_lines), 'doc_type': 'after_visit_summary', 'fields': fields, 'conflicting_fields': conflicts, 'warnings': warnings_out, 'requires_review': True, 'engine': 'opencv+tesseract-local', 'privacy': 'Only medication-related OCR fragments are returned. Other lines are omitted; this is not a complete de-identification guarantee.'}
