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


# Patient-portal exports put labels mid-line ("Health Plan Member name: …") and add more identifiers.
_INLINE_LABEL = re.compile(
    r"(?P<label>\b(?:member\s+name|patient\s+name|date\s+of\s+birth|dob|mrn|ceid|csn|account\s*(?:#|number)?|"
    r"ssn|member\s+id)\s*[:#])[ \t]*(?P<value>(?!\[)[^\n]*?)(?=\s{2,}|$)",
    re.IGNORECASE | re.MULTILINE,
)
_NAME_LABEL = re.compile(r"\b(?:member|patient)\s+name\s*:\s*(?P<name>[A-Za-z][A-Za-z .'-]{1,60}?)\s*$",
                         re.IGNORECASE | re.MULTILINE)
# Clinician names in capitals before a credential, possibly wrapped onto the next line.
_CLINICIAN = re.compile(r"\b(?:[A-Z][A-Z'.-]+[ \t]*\n?[ \t]*){1,4}(?:MD|DO|PT|DPT|NP|PA-C|PA|RN|OD|DPM)\b")
_PHONE = re.compile(r"(?<!\d)(?:\(\d{3}\)\s*|\b\d{3}[-.\s])\d{3}[-.]\d{4}\b")
_STREET = re.compile(r"^[ \t]*\d{1,6}[ \t]+[A-Z0-9][A-Za-z0-9 .]*\b(?:STREET|ST|AVENUE|AVE|BOULEVARD|BLVD|ROAD|RD|"
                     r"DRIVE|DR|WAY|LANE|LN|COURT|CT|PLACE|PL)\b\.?[^\n]*$", re.IGNORECASE | re.MULTILINE)
_CITY_ZIP = re.compile(r"^[ \t]*[A-Za-z .]+[ \t]+[A-Z]{2}[ \t]+\d{5}(?:-\d{4})?[ \t]*$", re.MULTILINE)
_URL = re.compile(r"https?://\S+")
# A run of short all-caps lines (6+) is a problem/diagnosis list: unrelated, sensitive history.
_CAPS_LINE = re.compile(r"^[ \t]*[A-Z][A-Z0-9 ,.()/'&-]{2,70}[ \t]*$")
_PROBLEM_LIST_MIN = 6


def _drop_problem_lists(text: str) -> tuple[str, int]:
    lines, out, run, count = text.split("\n"), [], [], 0

    def flush():
        nonlocal count
        if len(run) >= _PROBLEM_LIST_MIN:
            out.append("[problem list removed]")
            count += 1
        else:
            out.extend(run)
        run.clear()

    for line in lines:
        if _CAPS_LINE.match(line) and any(c.isalpha() for c in line):
            run.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out), count


def redact(text: str) -> tuple[str, int]:
    """Remove identifiers before any text reaches an LLM. Returns (text, count).

    Handles simple "Name: …" lines and patient-portal exports (mid-line labels, CEID/CSN, clinician
    names, phones, street addresses, portal links, and diagnosis/problem lists). A courtesy layer for
    demo documents, not a de-identification guarantee.
    """
    count = 0

    def bump(n: int = 1) -> None:
        nonlocal count
        count += n

    # The patient's own name, wherever else it appears (e.g. "Jordan Q. Testperson", "Jordan Testperson").
    names = [m.group("name").strip() for m in _NAME_LABEL.finditer(text)
             if m.group("name").strip() != REDACTED]
    for full in names:
        parts = [p.strip(".") for p in full.split() if len(p.strip(".")) > 1]
        for part in parts:
            text, n = re.subn(rf"\b{re.escape(part)}\b", "[PATIENT]", text, flags=re.IGNORECASE)
            bump(n)
        text = re.sub(r"\[PATIENT\](?:\s+[A-Z]\.?)?\s+\[PATIENT\]", "[PATIENT]", text)

    def _line(m: re.Match) -> str:
        if m.group("value").strip() in (REDACTED, "[PATIENT]"):
            return m.group(0)
        bump()
        return f"{m.group('label')} {REDACTED}"

    text = _IDENTIFIER_LINE.sub(_line, text)

    def _inline(m: re.Match) -> str:
        value = m.group("value").strip()
        if not value or value.startswith("[") or value == REDACTED:
            return m.group(0)
        bump()
        return f"{m.group('label')} {REDACTED}"

    text = _INLINE_LABEL.sub(_inline, text)
    for pattern, token in ((_URL, "[LINK]"), (_CLINICIAN, "[CLINICIAN]"), (_PHONE, "[PHONE]"),
                           (_STREET, "[ADDRESS]"), (_CITY_ZIP, "[ADDRESS]")):
        text, n = pattern.subn(token, text)
        bump(n)
    text, n = _drop_problem_lists(text)
    bump(n)
    return text, count


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
