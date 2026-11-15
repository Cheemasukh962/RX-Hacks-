"""Live extraction + conflict detection vs hand-labeled fixtures -> ml/artifacts/extraction_eval.json

Runs the real pipeline (redact -> OpenAI extraction -> quote verification -> reconcile) on each
seeded document pair and compares against *.expected.json. Instruction ids differ between
the LLM and the hand labels, so conflicts are matched by (type, drug names or kinds).

Run from backend/:  python -m ml.eval_extraction
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import extract, ingest, llm, reconcile, store
from app.classifier import ARTIFACTS_DIR
from app.schemas import Document, Instruction


def _conflict_key(c, by_id: dict[str, Instruction]) -> tuple:
    parts = []
    for iid in c.instruction_ids:
        ins = by_id[iid]
        parts.append(reconcile.canonical_name(ins.medication_name) or ins.kind)
    return (c.type, tuple(sorted(parts)))


def _med_key(ins: Instruction, doc_type: str) -> tuple:
    return (doc_type, reconcile.canonical_name(ins.medication_name))


def main() -> dict:
    if not llm.available():
        raise SystemExit("OPENAI_API_KEY not set (or REXO_DISABLE_LLM=1).")
    cases, tp, fp, fn = [], 0, 0, 0
    field_hits = field_total = 0
    for name in store.DEMO_FIXTURES:
        spec, gold = store.load_fixture(name)
        docs = []
        for d in spec["documents"]:
            raw = (store.FIXTURES_DIR / d["file"]).read_text(encoding="utf-8")
            text, _ = ingest.redact(raw)
            docs.append(Document(id=d["id"], type=d["type"], title=d["title"], text=text))
        instructions, stats = extract.extract(docs)
        instructions = instructions or []
        conflicts = reconcile.find_conflicts(docs, instructions)

        gold_by = {i.id: i for i in gold.instructions}
        pred_by = {i.id: i for i in instructions}
        g = {_conflict_key(c, gold_by) for c in gold.conflicts}
        p = {_conflict_key(c, pred_by) for c in conflicts}
        tp, fp, fn = tp + len(g & p), fp + len(p - g), fn + len(g - p)

        types = {d.id: d.type for d in docs}
        gold_meds = {_med_key(i, types[i.evidence.document_id]): i for i in gold.instructions if i.kind == "medication"}
        pred_meds = {_med_key(i, types[i.evidence.document_id]): i for i in instructions if i.kind == "medication"}
        fields = []
        for key, gi in gold_meds.items():
            pi = pred_meds.get(key)
            for f in ("strength", "frequency_per_day", "action"):
                field_total += 1
                ok = pi is not None and getattr(pi, f) == getattr(gi, f)
                field_hits += ok
                if not ok:
                    fields.append({"medication": key, "field": f, "expected": getattr(gi, f),
                                   "got": getattr(pi, f) if pi else "MISSING"})
        all_quotes_grounded = all(i.evidence.quote in next(d.text for d in docs if d.id == i.evidence.document_id)
                                  for i in instructions)
        cases.append({"case": spec["case_id"], "expected_conflicts": sorted(map(list, g)),
                      "found_conflicts": sorted(map(list, p)), "instructions_extracted": len(instructions),
                      "all_quotes_grounded": all_quotes_grounded, "pipeline_stats": stats,
                      "medication_field_mismatches": fields})
        print(f"{name:10s} expected {sorted(g)}  found {sorted(p)}  grounded={all_quotes_grounded}  {stats}")

    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": llm.DEFAULT_MODEL,
        "description": "Live OpenAI extraction + code-based conflict detection on the 3 hand-labeled "
                       "synthetic fixture pairs. Tiny n; shows the pipeline works end to end.",
        "conflicts": {"tp": tp, "fp": fp, "fn": fn, "precision": round(prec, 3), "recall": round(rec, 3)},
        "medication_fields": {"correct": field_hits, "total": field_total},
        "cases": cases,
    }
    (ARTIFACTS_DIR / "extraction_eval.json").write_text(json.dumps(result, indent=2, ensure_ascii=False),
                                                        encoding="utf-8")
    print(f"conflicts P={prec:.2f} R={rec:.2f} (tp {tp}, fp {fp}, fn {fn}); med fields {field_hits}/{field_total}")
    return result


if __name__ == "__main__":
    main()
