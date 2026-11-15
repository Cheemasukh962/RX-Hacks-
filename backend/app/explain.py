"""Styled, source-grounded explanations + tap-to-define (PLAN.md step 6).

Phase 1: deterministic templates built only from extracted fields and quotes.
Phase 2 will add LLM wording; the fact check below stays on whatever text is produced.
"""
from __future__ import annotations

from typing import Optional

from . import learning
from .reconcile import conflicts_for, parse_amount
from .safety import fact_check, fold
from .schemas import CarePlan, Citation, DefinedTerm, Instruction, PatientProfile

GLOSSARY: dict[str, dict[str, str]] = {
    "inflammation": {"en": "Swelling and irritation the body makes after an injury or surgery.",
                     "es": "Hinchazón e irritación que el cuerpo produce después de una lesión o cirugía."},
    "graft rejection": {"en": "When the body's defenses attack transplanted tissue, like a new cornea.",
                        "es": "Cuando las defensas del cuerpo atacan un tejido trasplantado, como una córnea nueva."},
    "steroid": {"en": "A medicine that calms swelling and irritation.",
                "es": "Un medicamento que calma la hinchazón y la irritación."},
    "ophthalmic": {"en": "Made to be used in the eye.", "es": "Hecho para usarse en el ojo."},
    "suspension": {"en": "A liquid medicine with tiny particles; shake it before use.",
                   "es": "Un medicamento líquido con partículas pequeñas; agítelo antes de usarlo."},
    "keratoplasty": {"en": "Corneal transplant surgery.", "es": "Cirugía de trasplante de córnea."},
    "nsaids": {"en": "A group of pain relievers that includes ibuprofen and naproxen.",
               "es": "Un grupo de analgésicos que incluye ibuprofeno y naproxeno."},
    "basic metabolic panel": {"en": "A blood test that checks kidney function and salts like potassium.",
                              "es": "Un análisis de sangre que revisa los riñones y sales como el potasio."},
    "a1c": {"en": "A blood test that shows your average blood sugar over about 3 months.",
            "es": "Un análisis de sangre que muestra su azúcar promedio de unos 3 meses."},
    "hypertension": {"en": "High blood pressure.", "es": "Presión arterial alta."},
    "as needed": {"en": "Only when you need it, not on a fixed schedule.",
                  "es": "Solo cuando lo necesite, no en un horario fijo."},
}

_FREQ = {
    "en": {1: "once a day", 2: "twice a day", 3: "three times a day", 4: "four times a day"},
    "es": {1: "una vez al día", 2: "dos veces al día", 3: "tres veces al día", 4: "cuatro veces al día"},
}
_UNIT_ES = {"drop": "gota", "tablet": "tableta", "capsule": "cápsula"}
_DUE_ES = {"day": "día", "days": "días", "week": "semana", "weeks": "semanas",
           "month": "mes", "months": "meses"}
_ROUTE = {"en": {"ophthalmic": "in the eye", "oral": "by mouth"},
          "es": {"ophthalmic": "en el ojo", "oral": "por la boca"}}

T = {
    "en": {
        "unknown": "not in your documents", "how_much": "How much", "how_often": "How often",
        "how_long": "How long", "says": "Your {title} says", "avoid": "Your {title} says to avoid {name}.",
        "conflict": "Your two documents disagree about this. REXO will not pick one. "
                    "Please ask your care team which is right.",
        "follow_up": "Follow-up visit", "lab": "Lab test", "when": "when",
        "warning": "Call your care team if you notice any of these", "care": "Daily care",
        "analogy_note": "(Analogy wording arrives with the AI writer; showing the detailed version.)",
    },
    "es": {
        "unknown": "no está en sus documentos", "how_much": "Cuánto", "how_often": "Con qué frecuencia",
        "how_long": "Por cuánto tiempo", "says": "Su {title} dice (en inglés)",
        "avoid": "Su {title} dice que evite {name}.",
        "conflict": "Sus dos documentos no coinciden en esto. REXO no elegirá uno. "
                    "Pregunte a su equipo de atención cuál es el correcto.",
        "follow_up": "Cita de seguimiento", "lab": "Análisis", "when": "cuándo",
        "warning": "Llame a su equipo de atención si nota alguno de estos signos", "care": "Cuidado diario",
        "analogy_note": "(La versión con comparaciones llega con el asistente de IA; se muestra la versión detallada.)",
    },
}

_DOC_TITLE = {"en": {"after_visit_summary": "after-visit summary", "clinical_note": "clinical note"},
              "es": {"after_visit_summary": "resumen de la visita", "clinical_note": "nota clínica"}}


def _dose_text(dose: Optional[str], lang: str) -> Optional[str]:
    if not dose:
        return None
    amt = parse_amount(dose)
    if lang == "es" and amt and amt[1] in _UNIT_ES:
        return f"{amt[0]:g} {_UNIT_ES[amt[1]]}{'s' if amt[0] != 1 else ''}"
    return dose


def _due_text(due: Optional[str], lang: str) -> Optional[str]:
    if not due or lang != "es":
        return due
    parts = due.split()
    return " ".join(_DUE_ES.get(p.lower(), p) for p in parts)


def _freq_text(n: Optional[int], lang: str) -> Optional[str]:
    if n is None:
        return None
    return _FREQ[lang].get(n, f"{n} times a day" if lang == "en" else f"{n} veces al día")


def _doc_title(plan: CarePlan, doc_id: str, lang: str) -> str:
    doc = next((d for d in plan.documents if d.id == doc_id), None)
    return _DOC_TITLE[lang][doc.type] if doc else doc_id


def _core_lines(plan: CarePlan, ins: Instruction, lang: str, detailed: bool) -> list[str]:
    t = T[lang]
    unk = t["unknown"]
    title = _doc_title(plan, ins.evidence.document_id, lang)
    lines: list[str] = []
    if ins.kind == "medication":
        name = (ins.medication_name or "").strip()
        name = name[:1].upper() + name[1:]
        if ins.action in ("avoid", "stop"):
            lines.append(t["avoid"].format(title=title, name=name))
        else:
            head = f"{name} {ins.strength}" if ins.strength else name
            route = _ROUTE[lang].get(ins.route or "", "")
            lines.append(f"{head}{' — ' + route if route else ''}.")
            lines.append(f"{t['how_much']}: {_dose_text(ins.dose, lang) or unk}.")
            lines.append(f"{t['how_often']}: {_freq_text(ins.frequency_per_day, lang) or unk}.")
            if detailed:
                lines.append(f"{t['how_long']}: {ins.duration or unk}.")
    elif ins.kind in ("follow_up", "lab"):
        lines.append(f"{t[ins.kind]} — {t['when']}: {_due_text(ins.due, lang) or unk}.")
    elif ins.kind == "warning_sign":
        lines.append(f"{t['warning']}.")
    else:
        lines.append(f"{t['care']}.")
    if detailed or ins.kind in ("warning_sign", "lifestyle", "supply"):
        lines.append(f"{t['says'].format(title=title)}: “{ins.evidence.quote}”")
    return lines


def defined_terms_for(texts: list[str], profile: PatientProfile) -> list[DefinedTerm]:
    hay = " ".join(fold(t) for t in texts)
    out = []
    for term, defs in GLOSSARY.items():
        if fold(term) in hay and learning.term_score(profile, term) < learning.DEFINE_BELOW:
            out.append(DefinedTerm(term=term, definition=defs[profile.language]))
    return out


def explain(plan: CarePlan, ins: Instruction, profile: PatientProfile,
            style: str) -> tuple[str, list[DefinedTerm], list[Citation], tuple[bool, list[str]]]:
    lang = profile.language
    detailed = style in ("detailed", "analogy")
    lines = _core_lines(plan, ins, lang, detailed)
    citations = [Citation(document_id=ins.evidence.document_id, quote=ins.evidence.quote)]
    conflicts = conflicts_for(ins.id, plan.conflicts)
    if conflicts:
        own = f"{T[lang]['says'].format(title=_doc_title(plan, ins.evidence.document_id, lang))}: “{ins.evidence.quote}”"
        if own not in lines:  # rule 3: a conflict always shows both quotes, in every style
            lines.append(own)
        lines.append(T[lang]["conflict"])
        by_id = {i.id: i for i in plan.instructions}
        for c in conflicts:
            for iid in c.instruction_ids:
                other = by_id.get(iid)
                if other and other.id != ins.id:
                    title = _doc_title(plan, other.evidence.document_id, lang)
                    lines.append(f"{T[lang]['says'].format(title=title)}: “{other.evidence.quote}”")
                    citations.append(Citation(document_id=other.evidence.document_id,
                                              quote=other.evidence.quote))
    if style == "analogy":
        lines.append(T[lang]["analogy_note"])
    text = "\n".join(lines)
    terms = defined_terms_for([text] + [c.quote for c in citations], profile)
    check = fact_check(text, [c.quote for c in citations])
    return text, terms, citations, check
