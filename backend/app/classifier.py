"""Teach-back + barrier classifier runtime (PLAN.md 8.2 / 8.3).

ML part only. Multilingual sentence embeddings (paraphrase-multilingual-MiniLM-L12-v2,
run through ONNX by fastembed, no PyTorch) feed one SGDClassifier (log loss) per label.

- Teach-back model input: [patient answer | instruction summary | |diff| | product].
  The instruction matters: "two drops" is only an error if the plan says one drop.
- Barrier model input: the patient's text.
- Barrier model supports partial_fit, so patient corrections update it live.

Training and evaluation scripts in ml/ import the same feature functions, so train-time
and run-time features cannot drift apart. If artifacts or the embedder are missing, the
API falls back to the rules pathway.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Optional

import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

log = logging.getLogger("rexo.classifier")

ML_DIR = Path(__file__).resolve().parent.parent / "ml"
ARTIFACTS_DIR = ML_DIR / "artifacts"
CACHE_DIR = ML_DIR / ".cache"
FEEDBACK_LOG = Path(os.getenv("REXO_FEEDBACK_LOG", str(ML_DIR / "data" / "feedback.jsonl")))
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

TB_LABELS = ["understood", "dose_error", "frequency_error", "duration_error", "stop_negation",
             "followup_timing_error", "uncertain"]
BR_LABELS = ["side_effect", "cost", "ran_out_refill", "forgot", "schedule_conflict",
             "doesnt_see_importance", "confusion", "wants_to_stop"]
THRESHOLD = 0.5


# ---------------------------------------------------------------- embeddings / features

_embedder = None
_embed_lock = threading.Lock()


def embedder():
    global _embedder
    with _embed_lock:
        if _embedder is None:
            from fastembed import TextEmbedding
            _embedder = TextEmbedding(EMBED_MODEL, cache_dir=str(CACHE_DIR))
    return _embedder


def embed(texts: list[str]) -> np.ndarray:
    E = np.array(list(embedder().embed(list(texts))), dtype=np.float32)
    return E / np.clip(np.linalg.norm(E, axis=1, keepdims=True), 1e-8, None)


def instruction_summary(ins: dict) -> str:
    """Canonical English text of an instruction. Must stay identical for train and run time."""
    parts = [ins.get("kind") or ""]
    for key in ("medication_name", "strength", "dose", "route"):
        if ins.get(key):
            parts.append(str(ins[key]))
    if ins.get("frequency_per_day") is not None:
        parts.append(f"{ins['frequency_per_day']} times per day")
    if ins.get("duration"):
        parts.append(f"for {ins['duration']}")
    if ins.get("due"):
        parts.append(f"in {ins['due']}")
    if ins.get("action"):
        parts.append(str(ins["action"]))
    return ", ".join(parts)


def teachback_features(texts: list[str], instructions: list[dict]) -> np.ndarray:
    A = embed(texts)
    B = embed([instruction_summary(i) for i in instructions])
    return np.hstack([A, B, np.abs(A - B), A * B])


def barrier_features(texts: list[str]) -> np.ndarray:
    return embed(texts)


# ---------------------------------------------------------------- model


class MultiLabelSGD:
    """One binary SGDClassifier (log loss) per label. Supports partial_fit for live updates."""

    def __init__(self, labels: list[str], alpha: float = 1e-4, seed: int = 0):
        self.labels = list(labels)
        self.alpha = alpha
        self.seed = seed
        self.models: dict[str, object] = {}
        self.constant: dict[str, float] = {}   # labels never / always positive in training

    def fit(self, X: np.ndarray, Y: np.ndarray, epochs: int = 30) -> "MultiLabelSGD":
        from sklearn.linear_model import SGDClassifier
        for j, label in enumerate(self.labels):
            y = Y[:, j].astype(int)
            pos = int(y.sum())
            if pos == 0 or pos == len(y):
                self.constant[label] = float(pos > 0)
                continue
            # dict class_weight (not "balanced") so later partial_fit calls are allowed
            w = {0: len(y) / (2 * (len(y) - pos)), 1: len(y) / (2 * pos)}
            clf = SGDClassifier(loss="log_loss", alpha=self.alpha, max_iter=epochs, tol=None,
                                class_weight=w, random_state=self.seed)
            clf.fit(X, y)
            self.models[label] = clf
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        out = np.zeros((X.shape[0], len(self.labels)), dtype=np.float32)
        for j, label in enumerate(self.labels):
            if label in self.models:
                out[:, j] = self.models[label].predict_proba(X)[:, 1]
            else:
                out[:, j] = self.constant.get(label, 0.0)
        return out

    def predict(self, X: np.ndarray, threshold: float = THRESHOLD) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)

    def partial_fit(self, X: np.ndarray, Y: np.ndarray, sample_weight=1.0,
                    eta0: Optional[float] = None) -> None:
        """eta0 switches to a small constant learning rate. Without it, live updates reuse the
        decayed "optimal" rate from training (~0.3), which times the class weight and example
        weight moved a whole label's intercept by ~20 in one correction."""
        from sklearn.linear_model import SGDClassifier
        sw = np.broadcast_to(np.asarray(sample_weight, dtype=np.float64), (X.shape[0],)).copy()
        for j, label in enumerate(self.labels):
            y = Y[:, j].astype(int)
            if label not in self.models:
                clf = SGDClassifier(loss="log_loss", alpha=self.alpha, random_state=self.seed)
                clf.partial_fit(X, y, classes=np.array([0, 1]), sample_weight=sw)
                self.models[label] = clf
                self.constant.pop(label, None)
            else:
                if eta0 is not None:
                    self.models[label].set_params(learning_rate="constant", eta0=eta0)
                self.models[label].partial_fit(X, y, sample_weight=sw)


# ---------------------------------------------------------------- runtime state

_models: dict[str, Optional[MultiLabelSGD]] = {"teachback": None, "barrier": None}
_state = {"tried": False, "error": None}
_model_lock = threading.RLock()


def enabled() -> bool:
    return os.getenv("REXO_DISABLE_ML", "").lower() not in ("1", "true", "yes")


def load(force: bool = False) -> bool:
    """Load trained artifacts (fresh from disk, which also undoes live updates)."""
    import joblib
    with _model_lock:
        if _state["tried"] and not force:
            return _models["barrier"] is not None
        _state["tried"] = True
        try:
            _models["teachback"] = joblib.load(ARTIFACTS_DIR / "teachback_clf.joblib")
            _models["barrier"] = joblib.load(ARTIFACTS_DIR / "barrier_clf.joblib")
            embed(["warmup"])
            _state["error"] = None
            return True
        except Exception as e:  # missing artifacts, no network for first model download, etc.
            _models["teachback"] = _models["barrier"] = None
            _state["error"] = f"{type(e).__name__}: {e}"
            log.warning("Classifier unavailable, using rules only: %s", _state["error"])
            return False


def available() -> bool:
    return enabled() and load()


def status() -> dict:
    return {"enabled": enabled(), "loaded": _models["barrier"] is not None, "error": _state["error"],
            "embedding_model": EMBED_MODEL}


def warmup_async() -> None:
    if enabled():
        threading.Thread(target=load, daemon=True).start()


def predict_teachback(text: str, instruction: dict) -> Optional[dict[str, float]]:
    if not available():
        return None
    with _model_lock:
        p = _models["teachback"].predict_proba(teachback_features([text], [instruction]))[0]
    return {label: float(p[j]) for j, label in enumerate(TB_LABELS)}


def predict_barrier(text: str) -> Optional[dict[str, float]]:
    if not available():
        return None
    with _model_lock:
        p = _models["barrier"].predict_proba(barrier_features([text]))[0]
    return {label: float(p[j]) for j, label in enumerate(BR_LABELS)}


REPLAY_SIZE = 150      # original training examples replayed with each correction
LIVE_ETA = 0.01        # constant learning rate for live corrections
_replay: dict[str, Optional[tuple[np.ndarray, np.ndarray]]] = {"barrier": None}


def _barrier_replay() -> Optional[tuple[np.ndarray, np.ndarray]]:
    """A fixed sample of barrier training data (embedded once, cached).

    Updating on the patient's one sentence alone drags every label's decision boundary
    toward it, so the corrected label then fires on unrelated sentences. Replaying a
    sample of the original data alongside it keeps the rest of the model where it was.
    """
    if _replay["barrier"] is None:
        import random
        rows = []
        path = ML_DIR / "data" / "train.jsonl"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                rows = [r for r in map(json.loads, f) if r.get("task") == "barrier"]
        if not rows:
            return None
        rows = random.Random(0).sample(rows, min(REPLAY_SIZE, len(rows)))
        X = barrier_features([r["text"] for r in rows])
        Y = np.array([[1 if l in r["labels"] else 0 for l in BR_LABELS] for r in rows])
        _replay["barrier"] = (X, Y)
    return _replay["barrier"]


def learn_barrier(text: str, labels: list[str], max_passes: int = 30) -> bool:
    """Patient-confirmed / corrected label -> partial_fit (classifier in the loop).

    Each pass trains on the patient's example (weighted) plus a replay sample of the
    original training data, until the model reproduces the patient's labels (capped).
    Returns True if the model's parameters changed.
    """
    if not available():
        return False
    X = barrier_features([text])
    Y = np.array([[1 if l in labels else 0 for l in BR_LABELS]])
    replay = _barrier_replay()
    if replay is not None:
        Xb, Yb = np.vstack([X, replay[0]]), np.vstack([Y, replay[1]])
        w = np.concatenate([[10.0], np.ones(len(replay[1]))])
    else:
        Xb, Yb, w = X, Y, 5.0
    with _model_lock:
        model = _models["barrier"]
        for _ in range(max_passes):
            model.partial_fit(Xb, Yb, sample_weight=w, eta0=LIVE_ETA)
            if (model.predict(X)[0] == Y[0]).all():
                break
    _log_feedback(text, labels)
    return True


def _log_feedback(text: str, labels: list[str]) -> None:
    try:
        FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FEEDBACK_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"task": "barrier", "text": text, "labels": labels,
                                "source": "patient_feedback"}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def reset() -> None:
    """Demo reset: drop live updates by reloading trained weights from disk."""
    if enabled() and _state["tried"]:
        load(force=True)
