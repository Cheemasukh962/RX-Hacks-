# ML data provenance

All data here is synthetic or written by the team. No real patient data.

| File | What | Source | In git |
|---|---|---|---|
| `train.jsonl` | Training set: teach-back answers + barrier statements, EN + ES | `python -m ml.build_dataset`: deterministic templates (seed 1115). Labels are correct by construction | yes |
| `synthetic_test.jsonl` | 20% of generated sentences, split by unique text | same generator → **optimistic** scores | yes |
| `train_paraphrased.jsonl` | 721 LLM paraphrases of 400 **train** rows (never test rows) | `python -m ml.augment_paraphrase` with gpt-5.4-mini, seed 2026. Labels are inherited from the source row; teach-back paraphrases whose rules-parsable dose/frequency/duration/timing contradicts the gold label were dropped (8 dropped, 71 duplicates dropped). `lang` is re-detected because the LLM sometimes translated | yes |
| `drugscom_sample.jsonl` | 700 real patient reviews (raw sample, ≤400 chars) | UCI ML Repository *Drug Review Dataset (Drugs.com)*, id 462, **CC BY 4.0** (Gräßer et al., 2018), via HF mirror `lewtun/drug-reviews` (the planned `Zakia/drugscom_reviews` mirror is no longer public). 35 seeded random offsets × 20 rows; UCI `uniqueID` kept per row | yes |
| `drugscom_labeled.jsonl` | Same reviews + 8 barrier labels. `split=train` (489) is used for training; `split=reviews_silver` (211) is an eval-only split | `python -m ml.fetch_drugscom`: **SILVER labels** from gpt-5.4-mini (batches of 20, review text wrapped as untrusted data). **Not hand-checked**, so treat them as approximate, not gold | yes |
| `heldout.csv` | **Hand-written held-out set** | Written by Sukhman and Amrit (~30–40 each), never shown to the generator | yes, once written |
| `feedback.jsonl` | Barrier labels patients confirmed or corrected in the app | `/api/feedback` → `classifier.learn_barrier` | no (runtime) |

## Writing the held-out set

```bash
cd backend
python -m ml.write_heldout      # interactive: pick case + instruction, type the answer, pick labels
python -m ml.evaluate           # re-score; the "heldout" split appears in eval_results.json
```

Rules for honest numbers:
- Don't open `ml/build_dataset.py` before writing. Write the way a real patient talks: typos, run-ons, vague answers, Spanglish.
- Mix languages: aim for about half Spanish.
- Cover every label, including hard ones (e.g. "with breakfast and dinner" = twice a day; "till my eye stops bugging me" = stop_negation).
- Teach-back answers are scored against the chosen instruction **only**. Document conflicts are ignored, because `source_conflict` is a rule, not a model label.
- After the eval is reported, don't edit held-out rows to make the model look better.

CSV columns: `author, task (teachback|barrier), lang (en|es), case_id, instruction_id, text, labels` (labels separated by `;`).

Teach-back labels: understood, dose_error, frequency_error, duration_error, stop_negation, followup_timing_error, uncertain
Barrier labels: side_effect, cost, ran_out_refill, forgot, schedule_conflict, doesnt_see_importance, confusion, wants_to_stop

## Model

- Embeddings: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, run with `fastembed` (ONNX, no PyTorch). Downloaded on first use to `ml/.cache/` (not in git).
- Classifier: one `SGDClassifier(loss="log_loss")` per label, class-weighted. The barrier model takes `partial_fit` updates from patient corrections.
- Retrain from cached data: `python -m ml.train` (about 30 s on CPU). Rebuild everything: `python -m ml.build_dataset && python -m ml.fetch_drugscom && python -m ml.augment_paraphrase && python -m ml.train`. The last two need `OPENAI_API_KEY` (about 75 calls total). Note: re-running `build_dataset` changes train rows, so re-run `augment_paraphrase` after it.

## Eval splits in `ml/artifacts/eval_results.json`

- `synthetic_test`: same templates as training → optimistic.
- `reviews_silver`: 211 real Drugs.com reviews, English only, barrier task only, **LLM silver labels**. Rare labels have tiny support (schedule_conflict 0, confusion 0, forgot 1, ran_out_refill 2), so per-label F1 there is not meaningful.
- `heldout`: hand-written gold set (when written). The honest number.
