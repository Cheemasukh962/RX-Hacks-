"""Document typing and identifier redaction (PLAN.md steps 1-2).

Redaction runs before any text is sent to an LLM. It is a courtesy step on
synthetic data, not a HIPAA control.
"""
from __future__ import annotations

import re
from typing import Optional

_IDENTIFIER_LINE = re.compile(
    r"^(?P<label>\s*(?:patient\s*name|name|nombre(?:\s+del\s+paciente)?|paciente|dob|d\.o\.b\.|"
    r"date\s+of\s+birth|fecha\s+de\s+nacimiento|mrn|medical\s+record\s+(?:number|no\.?)|"
    r"n[uú]mero\s+de\s+expediente|ssn|phone|tel[eé]fono|address|direcci[oó]n)\s*[:#])\s*(?P<value>.+)$",
    re.IGNORECASE | re.MULTILINE,
)

REDACTED = "[REDACTED]"

_AVS_SIGNALS = [
    "after visit summary", "after-visit summary", "your medications", "when to call",
    "reason for visit", "instructions for you", "resumen de la visita", "sus medicamentos",
    "cuándo llamar", "cuando llamar",
]
_NOTE_SIGNALS = [
    "clinical note", "progress note", "assessment", "subjective", "objective", "date of service",
    "plan:", "\nplan", "hpi", "history of present illness", "a/p", "nota clínica", "evaluación",
]


def redact(text: str) -> tuple[str, int]:
    """Replace the value on name / DOB / MRN-style lines. Returns (text, count)."""
    count = 0

    def _sub(m: re.Match) -> str:
        nonlocal count
        if m.group("value").strip() == REDACTED:
            return m.group(0)
        count += 1
        return f"{m.group('label')} {REDACTED}"

    return _IDENTIFIER_LINE.sub(_sub, text), count


def classify_document(text: str, type_hint: Optional[str] = None) -> str:
    """Heading-based AVS vs clinical-note typing. LLM fallback can be added in extract.py."""
    if type_hint in ("after_visit_summary", "clinical_note"):
        return type_hint
    low = text.lower()
    avs = sum(low.count(s) for s in _AVS_SIGNALS)
    note = sum(low.count(s) for s in _NOTE_SIGNALS)
    if avs == note:
        # Patient-facing second-person language leans AVS.
        avs += low.count(" your ") > 2
    return "after_visit_summary" if avs >= note else "clinical_note"


def default_title(doc_type: str, language: str = "en") -> str:
    return "After-Visit Summary" if doc_type == "after_visit_summary" else "Clinical Note"
