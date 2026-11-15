"""In-memory state + fixture loading + demo reset (PLAN.md section 4: no database)."""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Optional

from . import ingest
from .reconcile import build_tasks, find_conflicts
from .schemas import CarePlan, Document, Instruction, PatientProfile

BACKEND_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BACKEND_DIR / "fixtures"
ARTIFACTS_DIR = BACKEND_DIR / "ml" / "artifacts"

DEMO_FIXTURES = ["cornea", "medication", "matching"]

_lock = threading.RLock()
_cases: dict[str, CarePlan] = {}
_profiles: dict[str, PatientProfile] = {}
_examples: dict[str, dict] = {}         # barrier examples awaiting confirm / correct
_labeled: list[dict] = []               # patient-confirmed or corrected examples (for partial_fit)
_demo_meta: dict[str, dict] = {}        # case_id -> {title, description, fixture}


# ---------------------------------------------------------------- fixtures


def load_fixture(name: str) -> tuple[dict, CarePlan]:
    """Load <name>.expected.json + its text files and build a CarePlan.

    Conflicts and tasks are always computed by reconcile.py, never copied from the
    expected file, so the demo exercises the real code path.
    """
    spec = json.loads((FIXTURES_DIR / f"{name}.expected.json").read_text(encoding="utf-8"))
    documents = []
    for d in spec["documents"]:
        raw = (FIXTURES_DIR / d["file"]).read_text(encoding="utf-8")
        text, _ = ingest.redact(raw)
        documents.append(Document(id=d["id"], type=d["type"], title=d["title"], text=text))
    instructions = [Instruction(**i) for i in spec["instructions"]]
    conflicts = find_conflicts(documents, instructions)
    plan = CarePlan(case_id=spec["case_id"], synthetic=True, documents=documents,
                    instructions=instructions, conflicts=conflicts,
                    tasks=build_tasks(instructions, conflicts))
    return spec, plan


def fixture_raw_texts(name: str) -> list[str]:
    spec = json.loads((FIXTURES_DIR / f"{name}.expected.json").read_text(encoding="utf-8"))
    return [(FIXTURES_DIR / d["file"]).read_text(encoding="utf-8") for d in spec["documents"]]


def reset() -> None:
    with _lock:
        _cases.clear()
        _profiles.clear()
        _examples.clear()
        _labeled.clear()
        _demo_meta.clear()
        for name in DEMO_FIXTURES:
            spec, plan = load_fixture(name)
            _cases[plan.case_id] = plan
            _demo_meta[plan.case_id] = {"title": spec["title"], "description": spec["description"],
                                        "fixture": name}


# ---------------------------------------------------------------- cases


def demo_cases() -> list[dict]:
    return [{"case_id": cid, "title": m["title"], "description": m["description"]}
            for cid, m in _demo_meta.items()]


def get_case(case_id: str) -> Optional[CarePlan]:
    return _cases.get(case_id)


def save_case(plan: CarePlan) -> CarePlan:
    with _lock:
        _cases[plan.case_id] = plan
    return plan


def demo_case_copy(case_id: str) -> Optional[CarePlan]:
    """Fresh copy of a seeded case (undoes any task-status edits)."""
    meta = _demo_meta.get(case_id)
    if not meta:
        return None
    _, plan = load_fixture(meta["fixture"])
    return save_case(plan)


def match_fixture_by_text(texts: list[str]) -> Optional[str]:
    """If pasted documents are exactly a seeded pair, return that fixture name."""
    norm = sorted(t.strip() for t in texts)
    for name in DEMO_FIXTURES:
        if sorted(t.strip() for t in fixture_raw_texts(name)) == norm:
            return name
    return None


def new_case_id() -> str:
    return f"case-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------- profiles


def get_profile(profile_id: str) -> Optional[PatientProfile]:
    return _profiles.get(profile_id)


def get_or_create_profile(profile_id: str) -> PatientProfile:
    with _lock:
        if profile_id not in _profiles:
            _profiles[profile_id] = PatientProfile(profile_id=profile_id)
        return _profiles[profile_id]


def save_profile(profile: PatientProfile) -> PatientProfile:
    with _lock:
        _profiles[profile.profile_id] = profile
    return profile


def new_profile_id() -> str:
    return f"p-{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------- barrier examples


def save_example(example: dict) -> str:
    eid = f"ex-{uuid.uuid4().hex[:8]}"
    with _lock:
        _examples[eid] = {**example, "id": eid}
    return eid


def get_example(eid: str) -> Optional[dict]:
    return _examples.get(eid)


def add_labeled(example: dict) -> None:
    with _lock:
        _labeled.append(example)


def labeled_examples() -> list[dict]:
    return list(_labeled)


reset()
