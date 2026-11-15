"""Simulate the per-patient style bandit (PLAN.md 8.3, proof (b)). SIMULATION, not patient data.

Runs the production code (app.learning: seed_from_onboarding, choose_style, update_bandit)
on simulated patients and compares it with two baselines:

- adaptive:  Thompson sampling seeded from the patient's onboarding choice (what REXO does)
- fixed:     always the style the patient picked at onboarding, never adapts
- random:    a uniformly random allowed style each time

Simulated patient (all assumptions are written into the output file):
- one hidden "best" style among the styles their modes allow; teach-back success
  probability P_BEST with it, and a value drawn from [P_OTHER_LOW, P_OTHER_HIGH] with every other style
- the brief/detailed choice they make at onboarding matches their best style only
  P_ONBOARDING_RIGHT of the time (people do not always know what works for them)
- each round: REXO picks a style, the patient does a teach-back, success = reward 1.0 (weight 1.0)

Run from backend/:  python -m ml.simulate_bandit   → ml/artifacts/bandit_sim.json
"""
from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from app import learning
from app.schemas import PatientProfile

ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "bandit_sim.json"

N_PATIENTS = 100
ROUNDS = 20
REPEATS = 20              # independent runs with different seeds, to show spread
P_BEST = 0.85
P_OTHER_LOW, P_OTHER_HIGH = 0.35, 0.65
P_ONBOARDING_RIGHT = 0.5
MODE_OPTIONS = [["read"], ["read", "listen"], ["read", "visual"], ["read", "listen", "visual"]]
POLICIES = ["adaptive", "fixed", "random"]


def make_patient(rng: random.Random, pid: int) -> tuple[PatientProfile, dict[str, float], str]:
    modes = rng.choice(MODE_OPTIONS)
    profile = PatientProfile(profile_id=f"sim-{pid}", modes=modes)
    styles = learning.allowed_styles(profile)
    best = rng.choice(styles)
    p_success = {s: (P_BEST if s == best else rng.uniform(P_OTHER_LOW, P_OTHER_HIGH)) for s in styles}
    if best in ("brief", "detailed") and rng.random() < P_ONBOARDING_RIGHT:
        profile.detail = best
    else:
        profile.detail = rng.choice(["brief", "detailed"])
    learning.seed_from_onboarding(profile)
    return profile, p_success, best


def run_once(seed: int) -> dict:
    world = random.Random(seed)
    per_round = {p: [0] * ROUNDS for p in POLICIES}
    found_best = {p: 0 for p in POLICIES}
    for pid in range(N_PATIENTS):
        base, p_success, best = make_patient(world, pid)
        outcomes = [world.random() for _ in range(ROUNDS)]   # same luck for every policy (paired)
        for policy in POLICIES:
            profile = base.model_copy(deep=True)
            pick_rng = random.Random(f"{seed}-{pid}-{policy}")
            styles = learning.allowed_styles(profile)
            last = None
            for r in range(ROUNDS):
                if policy == "adaptive":
                    style, _ = learning.choose_style(profile, pick_rng)
                elif policy == "fixed":
                    style = profile.detail
                else:
                    style = pick_rng.choice(styles)
                success = outcomes[r] < p_success[style]
                per_round[policy][r] += success
                if policy == "adaptive":
                    learning.update_bandit(profile, style, 1.0 if success else 0.0, 1.0)
                last = style
            if policy == "adaptive":
                # "found" = the arm with the highest posterior mean is the true best style
                means = {s: a / (a + b) for s, (a, b) in profile.style_bandit.items() if s in styles}
                found_best[policy] += max(means, key=means.get) == best
            else:
                found_best[policy] += last == best
    return {"per_round": {p: [n / N_PATIENTS for n in v] for p, v in per_round.items()},
            "success_rate": {p: sum(v) / (N_PATIENTS * ROUNDS) for p, v in per_round.items()},
            "found_best": {p: v / N_PATIENTS for p, v in found_best.items()}}


def summarize(values: list[float]) -> dict:
    return {"mean": round(statistics.mean(values), 4), "min": round(min(values), 4), "max": round(max(values), 4)}


def main() -> dict:
    runs = [run_once(seed) for seed in range(REPEATS)]
    policies = {}
    for p in POLICIES:
        policies[p] = {
            "teachback_success_rate": summarize([r["success_rate"][p] for r in runs]),
            "ends_on_best_style": summarize([r["found_best"][p] for r in runs]),
            "success_by_round": [round(statistics.mean(r["per_round"][p][i] for r in runs), 4)
                                 for i in range(ROUNDS)],
        }
    first5 = lambda p: statistics.mean(policies[p]["success_by_round"][:5])
    last5 = lambda p: statistics.mean(policies[p]["success_by_round"][-5:])
    out = {
        "label": "SIMULATION: simulated patients and outcomes, not real patient data",
        "what": "Per-patient Thompson-sampling style bandit (app/learning.py, production code) vs baselines",
        "policies_description": {
            "adaptive": "REXO: Thompson sampling seeded from the onboarding choice, updated by teach-back",
            "fixed": "Always the onboarding style, never adapts",
            "random": "Uniformly random allowed style each time",
        },
        "assumptions": {
            "n_patients": N_PATIENTS, "rounds_per_patient": ROUNDS, "repeats": REPEATS,
            "p_success_best_style": P_BEST, "p_success_other_styles": [P_OTHER_LOW, P_OTHER_HIGH],
            "p_onboarding_choice_matches_best": P_ONBOARDING_RIGHT,
            "reward": "teach-back success = 1 (weight 1.0); thumbs not simulated",
        },
        "denominators": {"teachback_success_rate": f"{N_PATIENTS * ROUNDS} teach-backs per policy per run",
                         "ends_on_best_style": f"{N_PATIENTS} patients per run",
                         "spread": f"mean / min / max over {REPEATS} runs"},
        "policies": policies,
        "headline": {
            "adaptive_minus_fixed_success": round(policies["adaptive"]["teachback_success_rate"]["mean"]
                                                  - policies["fixed"]["teachback_success_rate"]["mean"], 4),
            "adaptive_first5_vs_last5": [round(first5("adaptive"), 4), round(last5("adaptive"), 4)],
            "fixed_first5_vs_last5": [round(first5("fixed"), 4), round(last5("fixed"), 4)],
        },
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    o = main()
    print(o["label"])
    for p, v in o["policies"].items():
        print(f"  {p:9} success {v['teachback_success_rate']['mean']:.3f} "
              f"(min {v['teachback_success_rate']['min']:.3f}, max {v['teachback_success_rate']['max']:.3f})  "
              f"ends on best style {v['ends_on_best_style']['mean']:.0%}")
    print("  headline:", o["headline"])
    print(f"wrote {ARTIFACT}")
