"""Doctor briefing draft (PLAN.md step 11). Editable, copy-only. Never sent automatically.

Phase 1: deterministic template (English + Spanish). Quotes stay in the source language.
"""
from __future__ import annotations

from .barrier import label_names
from .explain import _doc_title
from .schemas import CarePlan, Citation, PatientProfile


def build(plan: CarePlan, profile: PatientProfile, concern_refs: list[str],
          conflict_ids: list[str]) -> tuple[str, str, list[Citation]]:
    by_ins = {i.id: i for i in plan.instructions}
    conflicts = [c for c in plan.conflicts if c.id in conflict_ids]
    concern_by_id = {c.id: c for c in profile.concerns}
    concerns = []
    for ref in concern_refs:
        if ref in concern_by_id:
            concerns.append((concern_by_id[ref].text, concern_by_id[ref].labels))
        elif ref.strip():
            concerns.append((ref.strip(), []))

    citations: list[Citation] = []
    conflict_lines = {"en": [], "es": []}
    for c in conflicts:
        quotes = {"en": [], "es": []}
        for iid in c.instruction_ids:
            ins = by_ins.get(iid)
            if not ins:
                continue
            citations.append(Citation(document_id=ins.evidence.document_id, quote=ins.evidence.quote))
            for lang in ("en", "es"):
                quotes[lang].append(f"my {_doc_title(plan, ins.evidence.document_id, 'en')} says "
                                    f"“{ins.evidence.quote}”" if lang == "en" else
                                    f"mi {_doc_title(plan, ins.evidence.document_id, 'es')} dice "
                                    f"“{ins.evidence.quote}”")
        conflict_lines["en"].append("- " + ", but ".join(quotes["en"]) + " Which should I follow?")
        conflict_lines["es"].append("- " + ", pero ".join(quotes["es"]) + " ¿Cuál debo seguir?")

    def draft(lang: str) -> str:
        if lang == "es":
            lines = ["Hola, le escribo sobre mi visita reciente."]
            if conflict_lines["es"]:
                lines += ["", "Mis documentos no coinciden y necesito aclaración:"] + conflict_lines["es"]
            if concerns:
                lines += ["", "También quiero compartir una inquietud:"]
                for text, labels in concerns:
                    topic = f" (tema: {label_names(labels, 'es')})" if labels else ""
                    lines.append(f"- En mis palabras: “{text}”{topic}")
            lines += ["", "¿Podrían usted o el farmacéutico decirme qué debo hacer? Gracias.",
                      "", "(Las citas de mis documentos están en inglés, tal como aparecen en el original.)"]
            return "\n".join(lines)
        lines = ["Hello, I'm writing about my recent visit."]
        if conflict_lines["en"]:
            lines += ["", "My documents don't match and I need clarification:"] + conflict_lines["en"]
        if concerns:
            lines += ["", "I also want to share a concern:"]
            for text, labels in concerns:
                topic = f" (about: {label_names(labels, 'en')})" if labels else ""
                lines.append(f"- In my words: “{text}”{topic}")
        lines += ["", "Could you or the pharmacist let me know what I should do? Thank you."]
        return "\n".join(lines)

    en = draft("en")
    return en, draft(profile.language) if profile.language != "en" else en, citations
