"""Barrier capture (PLAN.md step 9): why a patient is struggling or wants to stop.

Phase 1 = keyword rules (EN + ES). Phase 3 adds the ML classifier + partial_fit on
patient corrections. Never gives treatment advice: acknowledge, ask, point to the care team.
"""
from __future__ import annotations

import re
from typing import Optional

from .safety import fold, is_urgent, urgent_message

BARRIER_LABELS = ["side_effect", "cost", "ran_out_refill", "forgot", "schedule_conflict",
                  "doesnt_see_importance", "confusion", "wants_to_stop"]

_KEYWORDS: dict[str, list[str]] = {
    "side_effect": [r"gritty", r"burn", r"sting", r"itch", r"blurr", r"side effect", r"dizz",
                    r"nause", r"rash", r"hurts?\b", r"makes? me (feel|sick)", r"upset stomach",
                    r"headache", r"cough", r"arenos", r"\barde\b", r"ardor", r"\bpica", r"borros",
                    r"efecto(s)? secundario", r"\bmare", r"nausea", r"me duele", r"me cae mal", r"\btos\b"],
    "cost": [r"expensive", r"afford", r"\bcost", r"price", r"money", r"insurance", r"copay",
             r"\bcaro", r"pagar", r"dinero", r"seguro medico", r"aseguranza", r"costo", r"precio"],
    "ran_out_refill": [r"ran out", r"run out", r"refill", r"out of (it|them|drops|pills)", r"pharmacy",
                       r"se me acab", r"resurt", r"receta", r"farmacia"],
    "forgot": [r"forg[eo]t", r"remember", r"slip(s|ped)? my mind", r"olvid", r"no me acuerdo", r"acordar"],
    "schedule_conflict": [r"\bwork\b", r"shift", r"schedule", r"busy", r"no time", r"travel",
                          r"trabajo", r"turno", r"horario", r"ocupad", r"no tengo tiempo"],
    "doesnt_see_importance": [r"don'?t (need|think i need)", r"feel fine", r"feels? fine", r"not working",
                              r"pointless", r"why do i (need|have)", r"doesn'?t (help|work)",
                              r"no (lo|la|los|las) necesito", r"me siento bien", r"no sirve", r"no funciona",
                              r"para que (lo|la|los|las) (uso|tomo|necesito)"],
    "confusion": [r"confus", r"don'?t understand", r"not sure (how|which|when)", r"which one",
                  r"no entiendo", r"confund", r"no se (como|cual|cuando)"],
    "wants_to_stop": [r"\bstop", r"\bquit", r"give up", r"not (going to|gonna) (use|take)",
                      r"dejar", r"parar", r"suspender", r"ya no (quiero|voy)"],
}
_COMPILED = {k: re.compile("|".join(v)) for k, v in _KEYWORDS.items()}

_NAMES = {
    "en": {"side_effect": "side effects", "cost": "cost", "ran_out_refill": "running out or refills",
           "forgot": "forgetting", "schedule_conflict": "your schedule",
           "doesnt_see_importance": "not sure it's needed", "confusion": "confusing instructions",
           "wants_to_stop": "thinking about stopping"},
    "es": {"side_effect": "efectos secundarios", "cost": "el costo", "ran_out_refill": "se acabó o resurtir",
           "forgot": "olvidos", "schedule_conflict": "su horario",
           "doesnt_see_importance": "no está seguro de que lo necesite",
           "confusion": "instrucciones confusas", "wants_to_stop": "está pensando en dejarlo"},
}


def classify_rules(text: str) -> list[str]:
    t = fold(text)
    return [label for label in BARRIER_LABELS if _COMPILED[label].search(t)]


def label_names(labels: list[str], lang: str) -> str:
    names = [_NAMES[lang][l] for l in labels if l in _NAMES[lang]]
    joiner = " and " if lang == "en" else " y "
    return joiner.join([", ".join(names[:-1]), names[-1]] if len(names) > 1 else names)


def combine(text: str, ml_probs: Optional[dict[str, float]] = None, threshold: float = 0.5) -> list[str]:
    """Union of keyword rules and ML predictions, in canonical label order."""
    found = set(classify_rules(text))
    if ml_probs:
        found |= {l for l, p in ml_probs.items() if p >= threshold}
    return [l for l in BARRIER_LABELS if l in found]


def respond(text: str, lang: str, ml_probs: Optional[dict[str, float]] = None) -> dict:
    if is_urgent(text):
        return {"labels": [], "urgent": True, "confirm_prompt": "", "support_text": urgent_message(lang)}
    labels = combine(text, ml_probs)
    if lang == "es":
        confirm = (f"Parece que le preocupa: {label_names(labels, 'es')}. ¿Es correcto?" if labels
                   else "No estoy seguro de haber entendido. ¿Qué le está dificultando el tratamiento?")
        support = "Gracias por decirlo. Lo que siente es importante."
        if "wants_to_stop" in labels or "side_effect" in labels:
            support += (" Antes de cambiar cómo usa un medicamento, comuníquese pronto con su equipo de "
                        "atención o farmacéutico. Ellos pueden ayudarle con lo que está sintiendo.")
        else:
            support += " Su equipo de atención o farmacéutico puede ayudar. REXO puede preparar un mensaje para ellos."
    else:
        confirm = (f"It sounds like this is about {label_names(labels, 'en')}. Is that right?" if labels
                   else "I'm not sure I understood. What is getting in the way?")
        support = "Thank you for telling me. What you're feeling matters."
        if "wants_to_stop" in labels or "side_effect" in labels:
            support += (" Before changing how you use a medicine, please contact your care team or "
                        "pharmacist soon. They can help with what you're experiencing.")
        else:
            support += " Your care team or pharmacist can help. REXO can draft a message for them."
    return {"labels": labels, "urgent": False, "confirm_prompt": confirm, "support_text": support}
