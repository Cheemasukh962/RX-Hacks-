"""Teach-back checking (PLAN.md 8.2).

Phase 1 = the rules pathway: parse numbers / time words (EN + ES) from the patient's
answer and compare them with the care plan, plus the source-conflict rule.
Phase 2 adds the ML classifier; then pathway becomes "ml" or "both".
"""
from __future__ import annotations

import re
from typing import Optional

from .explain import _doc_title, _dose_text, _freq_text
from .reconcile import CONFLICT_SLOT, _WORD_NUMBERS, conflicts_for, parse_amount, to_days
from .safety import fold
from .schemas import CarePlan, Instruction, SlotCheck

_COUNT_WORDS = {w: n for w, n in _WORD_NUMBERS.items() if w not in ("a", "an", "un", "una", "uno")}
_COUNT_RE = r"(\d+|" + "|".join(sorted(_COUNT_WORDS, key=len, reverse=True)) + r")"


def _count(tok: str) -> Optional[int]:
    return int(tok) if tok.isdigit() else _COUNT_WORDS.get(tok)


def parse_frequency(text: str) -> Optional[int]:
    """Times per day from a patient's sentence. None if not stated."""
    t = fold(text)
    m = re.search(rf"\b{_COUNT_RE}\s*(?:times|x|veces)\b", t)
    if m:
        return _count(m.group(1))
    m = re.search(rf"\b(?:every|cada)\s+{_COUNT_RE}\s*(?:hours|hrs|horas)\b", t)
    if m and _count(m.group(1)):
        return 24 // _count(m.group(1))
    if re.search(r"\btwice\b|\bdos veces\b", t):
        return 2
    if re.search(r"\bonce\b|\buna vez\b", t):
        return 1
    if re.search(r"(morning|manana).{0,25}(night|evening|noche|tarde)", t):
        return 2
    if re.search(r"\b(daily|every day|each day|a day|per day|al dia|diario|diaria|todos los dias|cada dia|"
                 r"every (morning|night|evening)|each (morning|night)|at bedtime|"
                 r"cada (manana|noche)|todas las (mananas|noches)|antes de dormir)\b", t):
        return 1
    return None


_STOP_EARLY = re.compile(
    r"stop (it |them |the drops |taking (it|them) )?(when|once|after|if)|until (it|i|my eye) feels? better|"
    r"when i feel better|only when (it|i)|quit (when|once)|"
    r"dejar(lo|la|los|las)? (cuando|si)|hasta que me sienta mejor|cuando me sienta mejor|"
    r"(lo|la|los|las) dejo cuando"
)
_UNCERTAIN = re.compile(r"not sure|don'?t know|no idea|can'?t remember|no se\b|no estoy segur|no me acuerdo|ni idea")


def _slot_result(said, documented) -> str:
    if said is None:
        return "not_mentioned"
    if documented is None:
        return "not_documented"
    return "correct" if said == documented else "incorrect"


def check(plan: CarePlan, ins: Instruction, response_text: str, lang: str,
          ml_probs: Optional[dict[str, float]] = None, threshold: float = 0.5) -> dict:
    """Rules pathway always runs. If ml_probs is given, ML fills gaps (pathway "ml"/"both")."""
    t = fold(response_text)
    conflicts = conflicts_for(ins.id, plan.conflicts)
    disputed = {CONFLICT_SLOT[c.type] for c in conflicts}

    # --- dose: compare against whichever field shares the patient's unit
    said_amt = parse_amount(response_text)
    dose_amt, strength_amt = parse_amount(ins.dose), parse_amount(ins.strength)
    if said_amt is None:
        dose = "not_mentioned"
    elif dose_amt and said_amt[1] == dose_amt[1]:
        dose = _slot_result(said_amt[0], dose_amt[0])
    elif strength_amt and said_amt[1] == strength_amt[1]:
        dose = _slot_result(said_amt[0], strength_amt[0])
    else:
        dose = "not_documented"

    frequency = _slot_result(parse_frequency(response_text), ins.frequency_per_day)
    duration = _slot_result(to_days(response_text), to_days(ins.duration))
    if duration == "not_documented" and ins.duration is None and to_days(response_text) is None:
        duration = "not_mentioned"

    followup = "not_mentioned"
    if ins.kind in ("follow_up", "lab"):
        followup = _slot_result(to_days(response_text), to_days(ins.due))
        duration = "not_mentioned"  # "in 2 weeks" is timing, not a course length

    # --- source-conflict rule: never confirm or correct a slot the documents disagree on
    if "action" in disputed:
        dose = frequency = duration = "documents_disagree"
    if "dose" in disputed:
        dose = "documents_disagree"
    if "frequency" in disputed:
        frequency = "documents_disagree"
    if "duration" in disputed:
        duration = "documents_disagree"
    if "due" in disputed and followup != "not_mentioned":
        followup = "documents_disagree"

    slots = {"dose_error": dose, "frequency_error": frequency, "duration_error": duration,
             "followup_timing_error": followup}
    source: dict[str, str] = {}   # label -> "rules" | "ml"

    # 1. Rules: every slot whose number they could parse is decided by code.
    for label, result in slots.items():
        if result == "incorrect":
            source[label] = "rules"
    can_stop = ins.action not in ("stop", "avoid") and "action" not in disputed
    if _STOP_EARLY.search(t) and can_stop:
        source["stop_negation"] = "rules"
    if _UNCERTAIN.search(t):
        source["uncertain"] = "rules"

    # 2. ML fills gaps the rules could not parse; it never overrides a parsed or disputed slot.
    if ml_probs:
        for label, result in slots.items():
            if result == "not_mentioned" and ml_probs.get(label, 0) >= threshold and label not in source:
                if not (label == "followup_timing_error" and ins.kind not in ("follow_up", "lab")):
                    source[label] = "ml"
        if can_stop and ml_probs.get("stop_negation", 0) >= threshold:
            source.setdefault("stop_negation", "ml")
        if ml_probs.get("uncertain", 0) >= threshold:
            source.setdefault("uncertain", "ml")

    errors = [l for l in ("dose_error", "frequency_error", "duration_error", "followup_timing_error",
                          "stop_negation") if l in source]
    evaluated = [s for s in slots.values() if s in ("correct", "incorrect")]
    if not errors and "uncertain" not in source:
        if evaluated:
            source["understood"] = "rules"
        elif ml_probs and ml_probs.get("understood", 0) >= threshold:
            source["understood"] = "ml"
        elif not conflicts:
            source["uncertain"] = "rules"   # nothing parseable and the model isn't confident either

    order = ["understood", "dose_error", "frequency_error", "duration_error", "stop_negation",
             "followup_timing_error", "uncertain"]
    labels = [l for l in order if l in source]
    if conflicts:
        labels.append("source_conflict")   # rule only, never ML

    used = set(source.values()) | ({"rules"} if conflicts else set())
    pathway = "both" if used == {"rules", "ml"} else ("ml" if used == {"ml"} else "rules")
    if ml_probs:
        # Model agreement with the final answer: mean ML probability of the returned labels.
        scored = [l for l in labels if l in ml_probs]
        confidence = round(sum(ml_probs[l] for l in scored) / len(scored), 3) if scored else 0.0
    else:
        # Rules only: 1.0 = a rule fired on a parsed value, 0.0 = nothing parsed. Not a probability.
        confidence = 1.0 if (evaluated or "stop_negation" in labels or conflicts) else 0.0

    return {
        "labels": labels,
        "confidence": confidence,
        "slot_check": SlotCheck(dose=dose, frequency=frequency, duration=duration),
        "source_conflict": bool(conflicts),
        "feedback_text": _feedback(plan, ins, labels, dose, frequency, followup, conflicts, lang),
        "pathway": pathway,
        "label_sources": source,
    }


_MSG = {
    "en": {
        "good": "Yes, that matches your documents.",
        "dose": "The amount doesn't match. Your documents say: {v}.",
        "freq": "How often doesn't match. Your documents say: {v}.",
        "dur": "How long doesn't match. Your documents say: {v}.",
        "fu": "The timing doesn't match. Your documents say: {v}.",
        "stop": "Your documents don't say to stop early. If you're thinking about stopping, "
                "please check with your care team or pharmacist first.",
        "conflict": "Your documents give different instructions here, so REXO can't say which is right. "
                    "Please ask your care team.",
        "unsure": "That's okay. Try saying how much you use and how often, in your own words.",
        "source": "Source",
    },
    "es": {
        "good": "Sí, eso coincide con sus documentos.",
        "dose": "La cantidad no coincide. Sus documentos dicen: {v}.",
        "freq": "La frecuencia no coincide. Sus documentos dicen: {v}.",
        "dur": "El tiempo no coincide. Sus documentos dicen: {v}.",
        "fu": "La fecha no coincide. Sus documentos dicen: {v}.",
        "stop": "Sus documentos no dicen que lo deje antes. Si está pensando en dejarlo, "
                "consulte primero con su equipo de atención o farmacéutico.",
        "conflict": "Sus documentos dan instrucciones diferentes aquí, así que REXO no puede decir cuál es "
                    "la correcta. Pregunte a su equipo de atención.",
        "unsure": "Está bien. Intente decir cuánto usa y con qué frecuencia, con sus propias palabras.",
        "source": "Fuente",
    },
}


def _feedback(plan, ins, labels, dose, frequency, followup, conflicts, lang) -> str:
    m = _MSG[lang]
    parts: list[str] = []
    if "dose_error" in labels:
        parts.append(m["dose"].format(v=_dose_text(ins.dose, lang) or ins.strength))
    if "frequency_error" in labels:
        parts.append(m["freq"].format(v=_freq_text(ins.frequency_per_day, lang)))
    if "duration_error" in labels:
        parts.append(m["dur"].format(v=ins.duration))
    if "followup_timing_error" in labels:
        parts.append(m["fu"].format(v=ins.due))
    if "stop_negation" in labels:
        parts.append(m["stop"])
    if conflicts:
        by_id = {i.id: i for i in plan.instructions}
        quotes = []
        for c in conflicts:
            for iid in c.instruction_ids:
                o = by_id[iid]
                quotes.append(f"{_doc_title(plan, o.evidence.document_id, lang)}: “{o.evidence.quote}”")
        parts.append(m["conflict"] + " " + " | ".join(dict.fromkeys(quotes)))
    if "understood" in labels and not conflicts:
        parts.insert(0, m["good"])
    elif "understood" in labels:
        parts.insert(0, m["good"].rstrip(".") + (" (where they agree)." if lang == "en" else " (donde coinciden)."))
    if "uncertain" in labels and not parts:
        parts.append(m["unsure"])
    if not conflicts and labels != ["uncertain"]:
        parts.append(f"{m['source']}: “{ins.evidence.quote}”")
    return " ".join(parts)
