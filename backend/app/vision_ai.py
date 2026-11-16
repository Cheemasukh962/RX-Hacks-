"""Bottle-label reading with an OpenAI vision model (primary reader; local Tesseract is the fallback).

The photo is decoded, downscaled and re-encoded in memory (which drops EXIF metadata such as GPS)
before it is sent. It is never written to disk or logged. The model is told to return only
medication fields, never the patient's name, Rx number, pharmacy, prescriber or address.
Values are unverified transcriptions that the patient must confirm.
"""
from __future__ import annotations

import base64
import io
from typing import Optional

import cv2
from PIL import Image

from . import llm
from .vision import decode_image, safe_preview

ENGINE = "openai-vision"
FIELDS = ("medication_name", "brand", "strength", "dosage_form", "directions",
          "food_instruction", "quantity", "refills", "discard_after")

SYSTEM = (
    "You read printed text on a photo of a prescription or over-the-counter medicine label. "
    "Transcribe only what is printed and legible; never guess, infer or fill in a value you cannot read. "
    "Return null for any field that is not visible. "
    "medication_name is the drug name as printed (generic name if shown, e.g. 'Meloxicam'). "
    "brand is the brand name only if printed (e.g. from 'Generic for: Mobic'). "
    "strength includes the unit (e.g. '15 mg'). directions are the dosing directions as printed. "
    "Never return the patient's name, date of birth, Rx/prescription number, pharmacy, prescriber, "
    "phone number or address, in any field. "
    "Set readable to false if the image does not show a legible medicine label."
)

_nullable = {"type": ["string", "null"]}
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"readable": {"type": "boolean"}, **{field: _nullable for field in FIELDS}},
    "required": ["readable", *FIELDS],
}


def _jpeg_data_url(payload: bytes) -> str:
    image = decode_image(payload)  # validates type/size, applies EXIF rotation, max 2200 px
    rgb = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    rgb.thumbnail((1600, 1600))
    out = io.BytesIO()
    rgb.save(out, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


def read_label(payload: bytes) -> Optional[dict]:
    """Return a scan in the same shape as vision.recognize_bottle, or None if OpenAI is unavailable.

    Raises vision.VisionError for an invalid image (same as the local reader).
    """
    if not llm.available():
        return None
    data_url = _jpeg_data_url(payload)
    result = llm.chat_json(
        SYSTEM,
        [{"type": "text", "text": "Read this medicine label."},
         {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}],
        SCHEMA, name="medicine_label", timeout=60.0,
    )
    if result is None:
        return None
    fields = []
    for field in FIELDS:
        value = (result.get(field) or "").strip()
        if value:
            fields.append({"field": field, "value": value,
                           "evidence": {"document_id": "bottle-label", "quote": value},
                           "ocr_confidence": None, "status": "needs_review", "supporting_passes": 1})
    lines = [field["value"] for field in fields]
    warnings_out = ["Unverified AI transcription. Check every field against the physical label before using it.",
                    "This reads printed text; it does not verify the bottle contents or recommend treatment."]
    if not result.get("readable") or not any(f["field"] == "medication_name" for f in fields):
        warnings_out.append("No medicine name could be read. Retake a closer, front-facing photo.")
    return {"mode": "live", "text": "\n".join(lines), "redacted_count": 0, "preview_png_b64": safe_preview(lines), "doc_type": "after_visit_summary",
            "fields": fields, "conflicting_fields": [], "warnings": warnings_out, "requires_review": True,
            "engine": ENGINE,
            "privacy": "The photo was sent to OpenAI for reading; only medication fields are returned."}
