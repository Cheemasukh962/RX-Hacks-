import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.safety import extract_numbers

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    client.post("/api/demo/reset")


def _case(cid):
    return client.post("/api/cases", json={"demo_case_id": cid}).json()


def test_demo_cases_and_modes():
    r = client.get("/api/demo-cases")
    assert r.status_code == 200
    ids = {c["case_id"] for c in r.json()}
    assert ids == {"demo-cornea-001", "demo-medication-002", "demo-matching-003"}
    assert all(c["mode"] in ("live", "demo") for c in r.json())


def test_cornea_case_shape():
    plan = _case("demo-cornea-001")
    assert plan["synthetic"] is True and plan["mode"] == "demo"
    assert [c["type"] for c in plan["conflicts"]] == ["frequency_mismatch"]
    assert client.get("/api/cases/demo-cornea-001").json()["case_id"] == "demo-cornea-001"
    assert client.get("/api/cases/nope").status_code == 404


def test_pasted_fixture_text_reproduces_case():
    from app import store
    texts = store.fixture_raw_texts("medication")
    plan = client.post("/api/cases", json={"documents": [{"text": t} for t in texts]}).json()
    assert plan["case_id"].startswith("case-")
    assert sorted(c["type"] for c in plan["conflicts"]) == ["action_mismatch", "dose_mismatch"]


def test_pasted_unknown_text_is_typed_and_redacted_but_not_invented():
    text = "AFTER VISIT SUMMARY\nPatient Name: Jane Roe\nYOUR MEDICATIONS\nAmoxicillin 500 mg three times daily."
    plan = client.post("/api/cases", json={"documents": [{"text": text}]}).json()
    assert plan["documents"][0]["type"] == "after_visit_summary"
    assert "Jane Roe" not in plan["documents"][0]["text"]
    assert plan["instructions"] == []


def test_profile_lifecycle():
    p = client.post("/api/profile", json={"language": "es", "detail": "detailed"}).json()
    pid = p["profile_id"]
    assert p["style_bandit"]["detailed"][0] > p["style_bandit"]["brief"][0]  # seeded from onboarding
    p = client.put(f"/api/profile/{pid}", json={"detail": "brief"}).json()
    assert p["detail"] == "brief" and p["language"] == "es"
    p = client.post(f"/api/profile/{pid}/reset").json()
    assert p["language"] == "en"
    assert client.get("/api/profile/missing").status_code == 404


def test_teachback_wrong_frequency_flagged():
    _case("demo-medication-002")
    r = client.post("/api/teachback", json={"case_id": "demo-medication-002", "profile_id": "p1",
                                            "instruction_id": "med-avs-1",
                                            "response_text": "I take one tablet twice a day"}).json()
    assert "frequency_error" in r["labels"]
    assert r["slot_check"]["frequency"] == "incorrect"
    assert r["slot_check"]["dose"] == "documents_disagree"  # 10 vs 20 mg is disputed
    assert r["source_conflict"] is True
    assert r["pathway"] == "rules"


def test_teachback_disputed_slot_never_confirmed_or_corrected():
    _case("demo-cornea-001")
    r = client.post("/api/teachback", json={"case_id": "demo-cornea-001", "profile_id": "p1",
                                            "instruction_id": "med-avs-1",
                                            "response_text": "One drop four times a day"}).json()
    assert r["slot_check"]["frequency"] == "documents_disagree"
    assert r["slot_check"]["duration"] == "not_mentioned"
    assert "frequency_error" not in r["labels"] and "source_conflict" in r["labels"]
    # brief explanation of a conflicted instruction still shows BOTH quotes
    e = client.post("/api/explain", json={"case_id": "demo-cornea-001", "profile_id": "p1",
                                          "instruction_id": "med-avs-1", "style_override": "brief"}).json()
    assert "four times daily" in e["text"] and "twice daily" in e["text"]


def test_teachback_correct_and_spanish():
    _case("demo-matching-003")
    body = {"case_id": "demo-matching-003", "profile_id": "p1", "instruction_id": "med-avs-1"}
    r = client.post("/api/teachback", json={**body, "response_text": "una tableta dos veces al día"}).json()
    assert r["labels"] == ["understood"]
    r = client.post("/api/teachback", json={**body, "response_text": "I'll stop when I feel better"}).json()
    assert "stop_negation" in r["labels"]


def test_barrier_gritty_and_urgent():
    _case("demo-cornea-001")
    r = client.post("/api/barrier", json={"case_id": "demo-cornea-001", "profile_id": "p1",
                                          "text": "These drops make my eye feel gritty. I'm thinking of stopping."}).json()
    assert set(r["labels"]) == {"side_effect", "wants_to_stop"}
    assert r["urgent"] is False and r["example_id"]
    assert "stop" not in r["support_text"].lower().replace("before changing", "")
    r = client.post("/api/barrier", json={"case_id": "demo-cornea-001", "profile_id": "p1",
                                          "text": "I have chest pain"}).json()
    assert r["urgent"] is True and "911" in r["support_text"]
    r = client.post("/api/barrier", json={"case_id": "demo-cornea-001", "profile_id": "p1",
                                          "text": "Perdí la vista de repente"}).json()
    assert r["urgent"] is True


def test_feedback_updates_profile_and_label_store():
    _case("demo-cornea-001")
    b = client.post("/api/barrier", json={"case_id": "demo-cornea-001", "profile_id": "p2",
                                          "text": "no tengo dinero para las gotas"}).json()
    assert "cost" in b["labels"]
    r = client.post("/api/feedback", json={"profile_id": "p2", "kind": "label_correct",
                                           "payload": {"example_id": b["example_id"], "labels": ["cost"]}}).json()
    assert r["profile"]["concerns"][0]["confirmed"] is True
    r = client.post("/api/feedback", json={"profile_id": "p2", "kind": "term_tap",
                                           "payload": {"term": "graft rejection"}}).json()
    assert r["profile"]["term_scores"]["graft rejection"] < 0.5
    before = r["profile"]["style_bandit"]["analogy"][0]
    r = client.post("/api/feedback", json={"profile_id": "p2", "kind": "thumbs",
                                           "payload": {"style": "analogy", "up": True}}).json()
    assert r["profile"]["style_bandit"]["analogy"][0] == pytest.approx(before + 0.3)


def test_explain_language_and_detail_never_change_numbers():
    """Acceptance: changing language or detail level never changes dose or frequency."""
    _case("demo-matching-003")
    numbers, citations = [], []
    for lang in ("en", "es"):
        client.post("/api/profile", json={"profile_id": f"p-{lang}", "language": lang})
        for style in ("brief", "detailed"):
            r = client.post("/api/explain", json={"case_id": "demo-matching-003", "profile_id": f"p-{lang}",
                                                  "instruction_id": "med-avs-1", "style_override": style}).json()
            assert r["fact_check"]["passed"], r
            core = r["text"].split("“")[0]  # exclude the verbatim quote
            numbers.append(extract_numbers(core) - {500.0})
            citations.append(r["citations"])
    assert all(n == numbers[0] for n in numbers), numbers
    assert all(c == citations[0] for c in citations)


def test_explain_conflict_shows_both_quotes_and_defines_terms():
    _case("demo-cornea-001")
    r = client.post("/api/explain", json={"case_id": "demo-cornea-001", "profile_id": "p3",
                                          "instruction_id": "med-avs-1"}).json()
    assert len(r["citations"]) == 2
    assert {c["document_id"] for c in r["citations"]} == {"avs-1", "note-1"}
    assert r["fact_check"]["passed"]
    assert any(t["term"] == "steroid" for t in r["defined_terms"])


def test_ask_in_and_out_of_documents():
    _case("demo-medication-002")
    body = {"case_id": "demo-medication-002", "profile_id": "p1"}
    r = client.post("/api/ask", json={**body, "question": "Can I keep taking ibuprofen?"}).json()
    assert r["in_documents"] and len(r["citations"]) == 2  # ibuprofen + NSAIDs class
    r = client.post("/api/ask", json={**body, "question": "Can I drink coffee?"}).json()
    assert r["in_documents"] is False and r["citations"] == []
    r = client.post("/api/ask", json={**body, "question": "I can't breathe"}).json()
    assert r["urgent"] is True


def test_briefing_includes_quotes_and_concern():
    _case("demo-cornea-001")
    client.post("/api/profile", json={"profile_id": "p4", "language": "es"})
    b = client.post("/api/barrier", json={"case_id": "demo-cornea-001", "profile_id": "p4",
                                          "text": "Las gotas me arden y quiero dejarlas"}).json()
    r = client.post("/api/briefing", json={"case_id": "demo-cornea-001", "profile_id": "p4",
                                           "include": {"concerns": [b["example_id"]], "conflicts": ["c1"]}}).json()
    assert "four times daily" in r["draft_en"] and "twice daily" in r["draft_en"]
    assert "Las gotas me arden" in r["draft_patient_language"]
    assert r["draft_en"] != r["draft_patient_language"]
    assert len(r["citations"]) == 2


def test_eval_and_unconfigured_services_are_honest():
    r = client.get("/api/eval").json()
    assert "available" in r and r["mode"] == "demo"
    assert client.post("/api/ingest/photo", files={"image": ("x.png", b"x", "image/png")}).status_code == 501
