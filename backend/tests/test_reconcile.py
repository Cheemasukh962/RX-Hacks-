import json

import pytest

from app import store
from app.reconcile import canonical_name, find_conflicts, parse_amount, same_drug, to_days
from app.schemas import Document, Evidence, Instruction


@pytest.mark.parametrize("name", store.DEMO_FIXTURES)
def test_fixture_quotes_match_source_exactly(name):
    spec = json.loads((store.FIXTURES_DIR / f"{name}.expected.json").read_text(encoding="utf-8"))
    texts = {d["id"]: (store.FIXTURES_DIR / d["file"]).read_text(encoding="utf-8") for d in spec["documents"]}
    ids = [i["id"] for i in spec["instructions"]]
    assert len(ids) == len(set(ids))
    for ins in spec["instructions"]:
        assert ins["evidence"]["quote"] in texts[ins["evidence"]["document_id"]], ins["id"]


@pytest.mark.parametrize("name", store.DEMO_FIXTURES)
def test_conflicts_match_hand_labels(name):
    spec, plan = store.load_fixture(name)
    got = sorted((c.type, tuple(c.instruction_ids), c.level) for c in plan.conflicts)
    want = sorted((c["type"], tuple(c["instruction_ids"]), c["level"]) for c in spec["expected_conflicts"])
    assert got == want


def test_cornea_one_frequency_conflict():
    _, plan = store.load_fixture("cornea")
    assert [c.type for c in plan.conflicts] == ["frequency_mismatch"]
    assert all(not c.resolved for c in plan.conflicts)


def test_medication_exactly_two_conflicts():
    _, plan = store.load_fixture("medication")
    assert sorted(c.type for c in plan.conflicts) == ["action_mismatch", "dose_mismatch"]


def test_matching_pair_zero_conflicts():
    _, plan = store.load_fixture("matching")
    assert plan.conflicts == []
    assert all(t.status == "open" for t in plan.tasks)


def test_conflicting_tasks_need_clarification():
    _, plan = store.load_fixture("medication")
    status = {t.instruction_id: t.status for t in plan.tasks}
    for iid in ("med-avs-1", "med-note-1", "med-avs-2", "med-note-2"):
        assert status[iid] == "needs_clarification"
    assert status["lab-avs-1"] == "open"
    assert "warn-avs-1" not in status  # warning signs are not checklist tasks


def test_redaction_applied_to_fixture_documents():
    _, plan = store.load_fixture("cornea")
    for d in plan.documents:
        assert "Alex Sample" not in d.text
        assert "[REDACTED]" in d.text


def test_parsers():
    assert to_days("1 week") == 7
    assert to_days("in two months") == 60
    assert to_days("10 días") == 10
    assert to_days(None) is None
    assert to_days("four times a day") is None  # frequency, not a duration
    assert to_days("dos veces al día") is None
    assert to_days("in a week") == 7
    assert parse_amount("10 mg") == (10.0, "mg")
    assert parse_amount("one drop") == (1.0, "drop")
    assert parse_amount("dos gotas") == (2.0, "drop")
    assert canonical_name("prednisolone acetate ophthalmic suspension") == "prednisolone"
    assert same_drug("NSAIDs", "ibuprofen")
    assert not same_drug("lisinopril", "metformin")


def _ins(iid, doc, **kw):
    return Instruction(id=iid, kind=kw.pop("kind", "medication"),
                       evidence=Evidence(document_id=doc, quote="q"), **kw)


DOCS = [Document(id="avs-1", type="after_visit_summary", title="a", text="q"),
        Document(id="note-1", type="clinical_note", title="n", text="q")]


def test_unit_mismatch_is_potential_not_confirmed():
    c = find_conflicts(DOCS, [_ins("a", "avs-1", medication_name="x drug", strength="1 g"),
                              _ins("b", "note-1", medication_name="x drug", strength="500 mg")])
    assert [(x.type, x.level) for x in c] == [("dose_mismatch", "potential_conflict")]


def test_missing_values_never_create_conflicts():
    c = find_conflicts(DOCS, [_ins("a", "avs-1", medication_name="drugx", frequency_per_day=2),
                              _ins("b", "note-1", medication_name="drugx")])
    assert c == []


def test_follow_up_date_mismatch():
    c = find_conflicts(DOCS, [_ins("a", "avs-1", kind="follow_up", due="1 week"),
                              _ins("b", "note-1", kind="follow_up", due="2 weeks")])
    assert [x.type for x in c] == ["date_mismatch"]


def test_start_vs_continue_is_not_a_conflict():
    c = find_conflicts(DOCS, [_ins("a", "avs-1", medication_name="drugx", action="start"),
                              _ins("b", "note-1", medication_name="drugx", action="continue")])
    assert c == []
