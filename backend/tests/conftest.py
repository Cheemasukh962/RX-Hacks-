import os
import tempfile

# API tests pin the deterministic rules pathway. tests/test_classifier.py turns ML back on.
os.environ.setdefault("REXO_DISABLE_ML", "1")
# Never let test corrections leak into ml/data/feedback.jsonl (train.py trains on it).
os.environ["REXO_FEEDBACK_LOG"] = os.path.join(tempfile.mkdtemp(), "feedback.jsonl")
# Tests never call OpenAI (cost, flakiness); live extraction is checked by ml/eval_extraction.py.
os.environ["REXO_DISABLE_LLM"] = "1"
