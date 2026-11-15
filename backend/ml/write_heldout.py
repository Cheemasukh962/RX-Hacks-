"""Interactive helper for writing the hand-written held-out set (ml/data/heldout.csv).

Run from backend/:  python -m ml.write_heldout

Write sentences the way a real patient would say them. Do NOT copy from the generator
templates in ml/build_dataset.py, and don't look at them first. That's what keeps
the held-out number honest.
"""
from __future__ import annotations

import csv
from pathlib import Path

from app import store
from app.classifier import BR_LABELS, TB_LABELS

CSV_PATH = Path(__file__).resolve().parent / "data" / "heldout.csv"
FIELDS = ["author", "task", "lang", "case_id", "instruction_id", "text", "labels"]
CASES = {"1": ("demo-cornea-001", "cornea"), "2": ("demo-medication-002", "medication"),
         "3": ("demo-matching-003", "matching")}


def _pick_labels(options: list[str]) -> list[str]:
    for i, l in enumerate(options, 1):
        print(f"   {i}. {l}")
    raw = input("  Label numbers, comma-separated (blank = none): ").strip()
    picked = []
    for tok in raw.replace(" ", "").split(","):
        if tok.isdigit() and 1 <= int(tok) <= len(options):
            picked.append(options[int(tok) - 1])
    return picked


def main() -> None:
    new = not CSV_PATH.exists()
    author = input("Your name (sukhman / amrit): ").strip().lower() or "unknown"
    count = 0
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        while True:
            print("\n--- new example (Ctrl+C to finish) ---")
            task = input("Task: [t]each-back or [b]arrier? ").strip().lower()
            if task not in ("t", "b"):
                continue
            lang = input("Language [en/es] (default en): ").strip().lower() or "en"
            row = {"author": author, "lang": lang, "case_id": "", "instruction_id": ""}
            if task == "t":
                row["task"] = "teachback"
                c = input("Case: 1=cornea  2=blood pressure  3=diabetes (matching): ").strip()
                if c not in CASES:
                    continue
                cid, fixture = CASES[c]
                _, plan = store.load_fixture(fixture)
                usable = [i for i in plan.instructions if i.kind in ("medication", "follow_up", "lab")]
                for n, ins in enumerate(usable, 1):
                    print(f"   {n}. [{ins.id}] {ins.evidence.quote}")
                k = input("  Instruction number: ").strip()
                if not k.isdigit() or not 1 <= int(k) <= len(usable):
                    continue
                row["case_id"], row["instruction_id"] = cid, usable[int(k) - 1].id
                print("  Tip: answers are scored against THIS instruction only (document conflicts ignored).")
                row["text"] = input("  Patient's answer, in their words: ").strip()
                row["labels"] = ";".join(_pick_labels(TB_LABELS))
            else:
                row["task"] = "barrier"
                row["text"] = input("  What the patient says is getting in the way: ").strip()
                row["labels"] = ";".join(_pick_labels(BR_LABELS))
            if row["text"]:
                w.writerow(row)
                f.flush()
                count += 1
                print(f"  saved ({count} this session)")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\nDone. File: {CSV_PATH}\nRe-score with: python -m ml.evaluate")
