"""Deterministic AVS-vs-clinical-note conflict detection (PLAN.md step 5).

Pure code, no LLM. It never decides which document is right. It only reports
where they disagree, so the patient can ask the care team.
"""
from __future__ import annotations

import re
from typing import Optional

from .schemas import Conflict, Document, Instruction, Task

# Drug classes the documents might name instead of a specific drug.
DRUG_CLASSES: dict[str, set[str]] = {
    "nsaid": {"ibuprofen", "naproxen", "aspirin", "diclofenac", "meloxicam", "ketorolac",
              "celecoxib", "indomethacin", "advil", "motrin", "aleve"},
    "steroid": {"prednisolone", "prednisone", "dexamethasone", "loteprednol", "difluprednate",
                "fluorometholone", "methylprednisolone"},
}

_NAME_STOPWORDS = {
    "tablet", "tablets", "capsule", "capsules", "oral", "ophthalmic", "suspension", "solution",
    "drops", "drop", "eye", "cream", "ointment", "take", "use", "start", "the", "and", "extended",
    "release", "hcl", "mg", "mcg",
}

_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fourteen": 14, "thirty": 30,
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "diez": 10, "doce": 12, "catorce": 14, "treinta": 30,
}

_UNIT_DAYS = {
    "day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30, "year": 365, "years": 365,
    "dia": 1, "dias": 1, "día": 1, "días": 1, "semana": 7, "semanas": 7, "mes": 30, "meses": 30,
    "año": 365, "años": 365,
}

_AMOUNT_UNITS = {
    "mg": "mg", "mcg": "mcg", "g": "g", "ml": "ml", "%": "%", "unit": "unit", "units": "unit",
    "drop": "drop", "drops": "drop", "gota": "drop", "gotas": "drop",
    "tablet": "tablet", "tablets": "tablet", "tableta": "tablet", "tabletas": "tablet",
    "pill": "tablet", "pills": "tablet", "pastilla": "tablet", "pastillas": "tablet",
    "capsule": "capsule", "capsules": "capsule", "puff": "puff", "puffs": "puff",
}

TAKE_ACTIONS = {"start", "continue", "change"}
NOT_TAKE_ACTIONS = {"stop", "avoid"}

CONFLICT_SLOT = {
    "dose_mismatch": "dose",
    "frequency_mismatch": "frequency",
    "duration_mismatch": "duration",
    "action_mismatch": "action",
    "date_mismatch": "due",
}


# ---------------------------------------------------------------- parsing helpers


def _num(token: str) -> Optional[float]:
    token = token.lower()
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return float(token)
    return float(_WORD_NUMBERS[token]) if token in _WORD_NUMBERS else None


_NUM_RE = r"\b(\d+(?:\.\d+)?|" + "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True)) + r")"


def to_days(text: Optional[str]) -> Optional[int]:
    """'1 week' -> 7, 'two months' -> 60, '10 días' -> 10. None if unparseable."""
    if not text:
        return None
    units = "|".join(sorted(_UNIT_DAYS, key=len, reverse=True))
    # "four times a day" / "per day" / "al día" are frequencies, not a 1-day duration.
    low = re.sub(r"\b(a|per|each|every|al|por|cada)\s+(day|dia|día)\b", " ", text.lower())
    m = re.search(_NUM_RE + r"\s*(" + units + r")\b", low)
    if not m:
        return None
    n = _num(m.group(1))
    return None if n is None else int(n * _UNIT_DAYS[m.group(2)])


def parse_amount(text: Optional[str]) -> Optional[tuple[float, str]]:
    """'10 mg' -> (10.0, 'mg'), '1 drop' -> (1.0, 'drop'), 'one tablet' -> (1.0, 'tablet')."""
    if not text:
        return None
    units = "|".join(re.escape(u) for u in sorted(_AMOUNT_UNITS, key=len, reverse=True))
    m = re.search(_NUM_RE + r"\s*(" + units + r")(?![a-z])", text.lower())
    if not m:
        return None
    n = _num(m.group(1))
    return None if n is None else (n, _AMOUNT_UNITS[m.group(2)])


def canonical_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    for tok in re.findall(r"[a-z]+", name.lower()):
        if tok in _NAME_STOPWORDS or len(tok) < 3:
            continue
        if tok.endswith("s") and tok[:-1] in DRUG_CLASSES:
            tok = tok[:-1]
        return tok
    return None


def same_drug(a: Optional[str], b: Optional[str]) -> bool:
    ca, cb = canonical_name(a), canonical_name(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    for cls, members in DRUG_CLASSES.items():
        if (ca == cls and cb in members) or (cb == cls and ca in members):
            return True
    return False


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


# ---------------------------------------------------------------- comparisons


def _compare_amount(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Returns a conflict level, or None if no disagreement / not enough data on both sides."""
    if not a or not b:
        return None
    pa, pb = parse_amount(a), parse_amount(b)
    if pa and pb:
        if pa[1] == pb[1]:
            return None if pa[0] == pb[0] else "confirmed_conflict"
        return "potential_conflict"  # different units: cannot compare safely
    return None if _norm(a) == _norm(b) else "potential_conflict"


def _compare_days(a: Optional[str], b: Optional[str]) -> Optional[str]:
    if not a or not b:
        return None
    da, db = to_days(a), to_days(b)
    if da is not None and db is not None:
        return None if da == db else "confirmed_conflict"
    return None if _norm(a) == _norm(b) else "potential_conflict"


def _action_group(action: Optional[str]) -> Optional[str]:
    if action in TAKE_ACTIONS:
        return "take"
    if action in NOT_TAKE_ACTIONS:
        return "not_take"
    return None


def _doc_types(documents: list[Document]) -> dict[str, str]:
    return {d.id: d.type for d in documents}


def find_conflicts(documents: list[Document], instructions: list[Instruction]) -> list[Conflict]:
    """Compare every AVS instruction against the matching clinical-note instruction."""
    types = _doc_types(documents)
    avs = [i for i in instructions if types.get(i.evidence.document_id) == "after_visit_summary"]
    note = [i for i in instructions if types.get(i.evidence.document_id) == "clinical_note"]

    found: list[tuple[str, list[str], str]] = []

    def add(ctype: str, a: Instruction, b: Instruction, level: Optional[str]) -> None:
        if level:
            found.append((ctype, [a.id, b.id], level))

    # Medications: pair by drug name (or drug class).
    for a in (i for i in avs if i.kind == "medication"):
        for b in (i for i in note if i.kind == "medication"):
            if not same_drug(a.medication_name, b.medication_name):
                continue
            ga, gb = _action_group(a.action), _action_group(b.action)
            if ga and gb and ga != gb:
                add("action_mismatch", a, b, "confirmed_conflict")
                continue  # "take" vs "don't take" already says everything; dose diffs are moot
            dose_level = _compare_amount(a.strength, b.strength) or _compare_amount(a.dose, b.dose)
            add("dose_mismatch", a, b, dose_level)
            if a.frequency_per_day is not None and b.frequency_per_day is not None \
                    and a.frequency_per_day != b.frequency_per_day:
                add("frequency_mismatch", a, b, "confirmed_conflict")
            add("duration_mismatch", a, b, _compare_days(a.duration, b.duration))

    # Follow-ups and labs: pair only when each document has exactly one of that kind
    # (we have no reliable name to match on, and guessing a pairing could invent a conflict).
    for kind in ("follow_up", "lab"):
        ka = [i for i in avs if i.kind == kind]
        kb = [i for i in note if i.kind == kind]
        if len(ka) == 1 and len(kb) == 1:
            add("date_mismatch", ka[0], kb[0], _compare_days(ka[0].due, kb[0].due))

    return [
        Conflict(id=f"c{n}", type=ctype, instruction_ids=ids, level=level, resolved=False)
        for n, (ctype, ids, level) in enumerate(found, start=1)
    ]


# ---------------------------------------------------------------- tasks


def _task_label(i: Instruction) -> str:
    if i.kind == "medication":
        name = (i.medication_name or "Medicine").strip()
        name = name[0].upper() + name[1:]
        if i.action in NOT_TAKE_ACTIONS:
            return f"Avoid {name}"
        if i.route == "ophthalmic":
            return f"{name} (eye drops)"
        return name
    return {
        "follow_up": "Follow-up visit",
        "lab": "Lab test",
        "lifestyle": "Daily care",
        "supply": "Supplies",
    }.get(i.kind, "Task")


def build_tasks(instructions: list[Instruction], conflicts: list[Conflict]) -> list[Task]:
    """One checklist task per actionable instruction. Warning signs are not tasks."""
    in_conflict = {iid for c in conflicts if not c.resolved for iid in c.instruction_ids}
    tasks: list[Task] = []
    for i in instructions:
        if i.kind == "warning_sign":
            continue
        status = "needs_clarification" if i.id in in_conflict else "open"
        tasks.append(Task(id=f"t{len(tasks) + 1}", instruction_id=i.id,
                          label=_task_label(i), status=status))
    return tasks


def conflicts_for(instruction_id: str, conflicts: list[Conflict]) -> list[Conflict]:
    return [c for c in conflicts if not c.resolved and instruction_id in c.instruction_ids]
