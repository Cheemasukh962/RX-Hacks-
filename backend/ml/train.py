"""Train the teach-back and barrier classifiers (PLAN.md 8.2).

Run from backend/:  python -m ml.train
Reads:  ml/data/train.jsonl (synthetic), train_paraphrased.jsonl (LLM paraphrases of train rows),
        drugscom_labeled.jsonl split=train (silver-labeled real reviews), feedback.jsonl (patient labels)
Writes: ml/artifacts/teachback_clf.joblib, barrier_clf.joblib, model_meta.json
Then runs ml.evaluate to write ml/artifacts/eval_results.json.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from app.classifier import (ARTIFACTS_DIR, BR_LABELS, EMBED_MODEL, FEEDBACK_LOG, TB_LABELS, MultiLabelSGD,
                            barrier_features, teachback_features)

DATA_DIR = Path(__file__).resolve().parent / "data"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def label_matrix(rows: list[dict], labels: list[str]) -> np.ndarray:
    return np.array([[1 if l in r["labels"] else 0 for l in labels] for r in rows], dtype=int)


def main() -> dict:
    t0 = time.time()
    train = read_jsonl(DATA_DIR / "train.jsonl")
    if not train:
        raise SystemExit("No ml/data/train.jsonl. Run: python -m ml.build_dataset")
    feedback = [r for r in read_jsonl(FEEDBACK_LOG) if r.get("task") == "barrier"]
    paraphrased = read_jsonl(DATA_DIR / "train_paraphrased.jsonl")          # LLM paraphrases of TRAIN rows
    reviews = [r for r in read_jsonl(DATA_DIR / "drugscom_labeled.jsonl")   # silver-labeled real reviews
               if r.get("split") == "train"]
    train = train + paraphrased

    tb = [r for r in train if r["task"] == "teachback"]
    br = [r for r in train if r["task"] == "barrier"] + reviews + feedback

    print(f"Embedding {len(tb)} teach-back + {len(br)} barrier examples with {EMBED_MODEL} ...")
    X_tb = teachback_features([r["text"] for r in tb], [r["instruction"] for r in tb])
    X_br = barrier_features([r["text"] for r in br])

    tb_model = MultiLabelSGD(TB_LABELS).fit(X_tb, label_matrix(tb, TB_LABELS))
    br_model = MultiLabelSGD(BR_LABELS).fit(X_br, label_matrix(br, BR_LABELS))

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(tb_model, ARTIFACTS_DIR / "teachback_clf.joblib")
    joblib.dump(br_model, ARTIFACTS_DIR / "barrier_clf.joblib")

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding_model": EMBED_MODEL,
        "classifier": "SGDClassifier(loss='log_loss') per label, class-weighted, threshold 0.5",
        "teachback": {"labels": TB_LABELS, "train_examples": len(tb),
                      "features": "embed(answer) | embed(instruction) | |diff| | product (1536 dims)",
                      "label_counts": {l: int(sum(l in r["labels"] for r in tb)) for l in TB_LABELS}},
        "sources": {"synthetic_templates": len(train) - len(paraphrased),
                    "llm_paraphrases": len(paraphrased), "drugscom_silver_reviews": len(reviews),
                    "patient_feedback": len(feedback)},
        "barrier": {"labels": BR_LABELS, "train_examples": len(br), "from_patient_feedback": len(feedback),
                    "features": "embed(text) (384 dims)",
                    "label_counts": {l: int(sum(l in r["labels"] for r in br)) for l in BR_LABELS}},
        "train_command": "python -m ml.build_dataset && python -m ml.fetch_drugscom && "
                         "python -m ml.augment_paraphrase && python -m ml.train",
        "seconds": round(time.time() - t0, 1),
    }
    (ARTIFACTS_DIR / "model_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved models to {ARTIFACTS_DIR} in {meta['seconds']}s")

    from ml import evaluate
    evaluate.main()
    return meta


if __name__ == "__main__":
    main()
