"""Per-patient self-learning (PLAN.md 8.3). Changes presentation only, never facts.

- Term familiarity: term_scores[term] in [0, 1]; 0 = confusing, 1 = known.
- Style bandit: Thompson sampling over STYLES with Beta(alpha, beta) per arm.
- Classifier-in-the-loop (partial_fit) lands in Phase 3; labeled examples are already stored.
"""
from __future__ import annotations

import random
from typing import Optional

from .schemas import STYLES, PatientProfile

DEFAULT_TERM_SCORE = 0.5
DEFINE_BELOW = 0.7          # define a term in explanations while its score is below this
ONBOARDING_PRIOR = 2.0      # pseudo-successes added to the style the patient picked at setup

# profile_id -> last style shown, so a teach-back result can reward the right arm
_last_style: dict[str, str] = {}


def term_score(profile: PatientProfile, term: str) -> float:
    return profile.term_scores.get(term.lower(), DEFAULT_TERM_SCORE)


def mark_term_confusing(profile: PatientProfile, term: str, rate: float = 0.5) -> None:
    s = term_score(profile, term)
    profile.term_scores[term.lower()] = round(s * (1 - rate), 3)


def mark_term_known(profile: PatientProfile, term: str, rate: float = 0.5) -> None:
    s = term_score(profile, term)
    profile.term_scores[term.lower()] = round(s + (1 - s) * rate, 3)


def update_bandit(profile: PatientProfile, style: str, reward: float, weight: float) -> None:
    """reward in [0, 1]; weight 1.0 = teach-back, 0.3 = thumbs (PLAN.md 8.3)."""
    if style not in profile.style_bandit:
        profile.style_bandit[style] = [1.0, 1.0]
    a, b = profile.style_bandit[style]
    profile.style_bandit[style] = [round(a + weight * reward, 3), round(b + weight * (1 - reward), 3)]


def seed_from_onboarding(profile: PatientProfile) -> None:
    """Seed the bandit from the patient's own stated choices (never from demographics)."""
    profile.style_bandit = {s: [1.0, 1.0] for s in STYLES}
    profile.style_bandit[profile.detail][0] += ONBOARDING_PRIOR
    if "listen" in profile.modes:
        profile.style_bandit["audio"][0] += 1.0
    if "visual" in profile.modes:
        profile.style_bandit["visual"][0] += 1.0


def allowed_styles(profile: PatientProfile) -> list[str]:
    styles = ["brief", "detailed", "analogy"]
    if "listen" in profile.modes:
        styles.append("audio")
    if "visual" in profile.modes:
        styles.append("visual")
    return styles


def choose_style(profile: PatientProfile, rng: Optional[random.Random] = None) -> tuple[str, str]:
    rng = rng or random.Random()
    best, best_draw = "brief", -1.0
    for s in allowed_styles(profile):
        a, b = profile.style_bandit.get(s, [1.0, 1.0])
        draw = rng.betavariate(max(a, 1e-3), max(b, 1e-3))
        if draw > best_draw:
            best, best_draw = s, draw
    a, b = profile.style_bandit.get(best, [1.0, 1.0])
    if profile.language == "es":
        why = (f"REXO eligió '{best}' según lo que ha funcionado para usted "
               f"(aciertos {a:g}, fallos {b:g}, incluida su elección inicial).")
    else:
        why = (f"REXO picked '{best}' from what has worked for you so far "
               f"(successes {a:g}, misses {b:g}, including your starting choice).")
    return best, why


def remember_style(profile_id: str, style: str) -> None:
    _last_style[profile_id] = style


def last_style(profile_id: str) -> Optional[str]:
    return _last_style.get(profile_id)


def reset() -> None:
    _last_style.clear()
