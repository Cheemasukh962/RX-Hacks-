"""Evaluate teach-back + barrier systems and write ml/artifacts/eval_results.json (PLAN.md 8.2).

Systems compared (same inputs, same metrics):
  teach-back:  keyword baseline | rules only | ML only | ML + rules (what the API runs)
  barrier:     keyword rules     | ML only    | ML + rules (union, what the API runs)

Splits:
  synthetic_test : held out from training, but made by the SAME templates -> optimistic.
  heldout        : ml/data/heldout.csv, hand-written by the team, never seen by the generator.
                   This is the honest number. Reported only when the file exists.

Run from backend/:  python -m ml.evaluate
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from app import barrier, store, teachback
from app.classifier import (ARTIFACTS_DIR, BR_LABELS, TB_LABELS, THRESHOLD, barrier_features,
                            teachback_features)
from app.safety import fold
from app.schemas import CarePlan, Evidence, Instruction

DATA_DIR = Path(__file__).resolve().parent / "data"
HELDOUT_CSV = DATA_DIR / "heldout.csv"
CASE_TO_FIXTURE = {"demo-cornea-001": "cornea", "demo-medication-002": "medication",
                   "demo-matching-003": "matching"}


# ---------------------------------------------------------------- data


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def read_heldout() -> list[dict]:
    """CSV columns: author, task, lang, case_id, instruction_id, text, labels (separated by ;)"""
    if not HELDOUT_CSV.exists():
        return []
    fixtures = {cid: store.load_fixture(name)[1] for cid, name in CASE_TO_FIXTURE.items()}
    rows = []
    with HELDOUT_CSV.open(encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f)):
            text = (r.get("text") or "").strip()
            task = (r.get("task") or "").strip()
            if not text or task not in ("teachback", "barrier"):
                continue
            labels = [l.strip() for l in (r.get("labels") or "").split(";") if l.strip()]
            row = {"id": f"heldout-{i:03d}", "task": task, "lang": (r.get("lang") or "en").strip(),
                   "text": text, "labels": labels, "author": (r.get("author") or "").strip(),
                   "instruction": None}
            if task == "teachback":
                plan = fixtures.get((r.get("case_id") or "").strip())
                ins = next((x for x in plan.instructions if x.id == (r.get("instruction_id") or "").strip()),
                           None) if plan else None
                if ins is None:
                    print(f"  skipping heldout row {i}: unknown case_id/instruction_id")
                    continue
                row["instruction"] = ins.model_dump()
            rows.append(row)
    return rows


# ---------------------------------------------------------------- systems


_KW_STOP = re.compile(r"\bstop|\bquit|until|dejar|dejo|hasta que")
_KW_UNSURE = re.compile(r"not sure|don'?t know|maybe|no idea|no se\b|tal vez|quizas|no estoy segur|no me acuerdo")


def keyword_teachback(text: str) -> list[str]:
    """Naive baseline: keyword spotting only, no number parsing, no instruction context."""
    t = fold(text)
    out = []
    if _KW_STOP.search(t):
        out.append("stop_negation")
    if _KW_UNSURE.search(t):
        out.append("uncertain")
    return out or ["understood"]


def _plan_for(ins_dict: dict) -> tuple[CarePlan, Instruction]:
    """Comprehension is scored without document conflicts (source_conflict is a rule, not a label
    the classifiers predict), so the instruction is placed in a conflict-free plan."""
    ins = Instruction(**{"id": "eval-ins", "evidence": Evidence(document_id="avs-1", quote="-"),
                         **{k: v for k, v in ins_dict.items() if k not in ("id", "evidence")}})
    return CarePlan(case_id="eval", documents=[], instructions=[ins]), ins


def _ml_only(probs: dict[str, float], labels: list[str]) -> list[str]:
    out = [l for l in labels if probs[l] >= THRESHOLD]
    return out or [max(labels, key=lambda l: probs[l])]


def run_teachback(rows: list[dict], model) -> dict[str, list[list[str]]]:
    preds = {"keyword_baseline": [], "rules_only": [], "ml_only": [], "ml_plus_rules": []}
    if not rows:
        return preds
    P = model.predict_proba(teachback_features([r["text"] for r in rows], [r["instruction"] for r in rows]))
    for r, p in zip(rows, P):
        probs = {l: float(p[j]) for j, l in enumerate(TB_LABELS)}
        plan, ins = _plan_for(r["instruction"])
        preds["keyword_baseline"].append(keyword_teachback(r["text"]))
        preds["rules_only"].append(teachback.check(plan, ins, r["text"], r["lang"])["labels"])
        preds["ml_only"].append(_ml_only(probs, TB_LABELS))
        preds["ml_plus_rules"].append(teachback.check(plan, ins, r["text"], r["lang"], ml_probs=probs)["labels"])
    return preds


def run_barrier(rows: list[dict], model) -> dict[str, list[list[str]]]:
    preds = {"keyword_rules": [], "ml_only": [], "ml_plus_rules": []}
    if not rows:
        return preds
    P = model.predict_proba(barrier_features([r["text"] for r in rows]))
    for r, p in zip(rows, P):
        probs = {l: float(p[j]) for j, l in enumerate(BR_LABELS)}
        preds["keyword_rules"].append(barrier.classify_rules(r["text"]))
        preds["ml_only"].append([l for l in BR_LABELS if probs[l] >= THRESHOLD])
        preds["ml_plus_rules"].append(barrier.combine(r["text"], probs))
    return preds


# ---------------------------------------------------------------- metrics


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3), "tp": tp, "fp": fp, "fn": fn}


def score(gold: list[list[str]], pred: list[list[str]], labels: list[str]) -> dict:
    per, TP, FP, FN = {}, 0, 0, 0
    for l in labels:
        tp = sum(l in g and l in p for g, p in zip(gold, pred))
        fp = sum(l not in g and l in p for g, p in zip(gold, pred))
        fn = sum(l in g and l not in p for g, p in zip(gold, pred))
        support = sum(l in g for g in gold)
        per[l] = {**_prf(tp, fp, fn), "support": support}
        TP, FP, FN = TP + tp, FP + fp, FN + fn
    with_support = [v["f1"] for v in per.values() if v["support"]]
    exact = sum(set(g) == set(p) for g, p in zip(gold, pred))
    return {"n": len(gold), "exact_match": exact, "exact_match_rate": round(exact / len(gold), 3) if gold else 0.0,
            "micro": _prf(TP, FP, FN),
            "macro_f1": round(sum(with_support) / len(with_support), 3) if with_support else 0.0,
            "per_label": per}


def _errors(rows, preds, k=12) -> list[dict]:
    out = []
    for r, p in zip(rows, preds):
        if set(r["labels"]) != set(p):
            out.append({"id": r["id"], "lang": r["lang"], "text": r["text"], "gold": r["labels"], "predicted": p,
                        "instruction": r["instruction"] and {k2: v for k2, v in r["instruction"].items()
                                                              if v is not None and k2 != "evidence"}})
            if len(out) >= k:
                break
    return out


def evaluate_split(rows: list[dict], tb_model, br_model) -> dict:
    tb = [r for r in rows if r["task"] == "teachback"]
    br = [r for r in rows if r["task"] == "barrier"]
    tb_preds, br_preds = run_teachback(tb, tb_model), run_barrier(br, br_model)
    return {
        "counts": {"teachback": len(tb), "barrier": len(br),
                   "by_language": {lang: sum(r["lang"] == lang for r in rows) for lang in ("en", "es")}},
        "teachback": {s: score([r["labels"] for r in tb], p, TB_LABELS) for s, p in tb_preds.items()} if tb else None,
        "barrier": {s: score([r["labels"] for r in br], p, BR_LABELS) for s, p in br_preds.items()} if br else None,
        "errors": {"teachback_ml_plus_rules": _errors(tb, tb_preds["ml_plus_rules"]) if tb else [],
                   "barrier_ml_plus_rules": _errors(br, br_preds["ml_plus_rules"]) if br else []},
    }


def main() -> dict:
    tb_model = joblib.load(ARTIFACTS_DIR / "teachback_clf.joblib")
    br_model = joblib.load(ARTIFACTS_DIR / "barrier_clf.joblib")
    meta = json.loads((ARTIFACTS_DIR / "model_meta.json").read_text(encoding="utf-8"))
    syn = read_jsonl(DATA_DIR / "synthetic_test.jsonl")
    held = read_heldout()
    silver = [r for r in read_jsonl(DATA_DIR / "drugscom_labeled.jsonl") if r.get("split") == "reviews_silver"]

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "framing": "Synthetic-task benchmark. It shows engineering; it does not validate patient "
                   "comprehension or medical safety.",
        "which_parts": {
            "ml": "Multilingual sentence embeddings + per-label SGDClassifier (teach-back and barrier).",
            "rules": "Number / time-word parsing (EN+ES) compared with the care plan; keyword lists for "
                     "barriers; source_conflict is rule-only and never predicted by ML.",
            "ml_plus_rules": "Teach-back: rules decide every slot they can parse, ML fills the gaps. "
                             "Barrier: union of keyword rules and ML.",
        },
        "model": meta,
        "splits": {
            "synthetic_test": {
                "description": "20% of generated sentences, held out from training. Same templates as "
                               "training, so this number is optimistic.",
                **evaluate_split(syn, tb_model, br_model)},
            "heldout": ({
                "description": "Hand-written by the team; never shown to the generator. The honest number.",
                "authors": {a: sum(r["author"] == a for r in held) for a in sorted({r["author"] for r in held})},
                **evaluate_split(held, tb_model, br_model)} if held else None),
            "reviews_silver": ({
                "description": "Real Drugs.com patient reviews (UCI id 462, CC BY 4.0), barrier task only. "
                               "Labels are SILVER: assigned by an LLM (gpt-5.4-mini), not hand-checked. "
                               "Never used for training (the other 70% of the labeled sample is).",
                **evaluate_split(silver, tb_model, br_model)} if silver else None),
        },
        "heldout_status": (f"{len(held)} hand-written examples" if held else
                           "Not written yet. Add rows to ml/data/heldout.csv (see ml/data/README.md)."),
    }
    out = ARTIFACTS_DIR / "eval_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    _print_summary(results)
    print(f"Wrote {out}")
    return results


def _print_summary(res: dict) -> None:
    for split, data in res["splits"].items():
        if not data:
            print(f"[{split}] not available")
            continue
        print(f"[{split}] {data['counts']}")
        for task in ("teachback", "barrier"):
            if data[task]:
                for system, m in data[task].items():
                    print(f"  {task:9s} {system:17s} micro-F1 {m['micro']['f1']:.3f}  macro-F1 {m['macro_f1']:.3f}"
                          f"  exact {m['exact_match']}/{m['n']}")


if __name__ == "__main__":
    main()
