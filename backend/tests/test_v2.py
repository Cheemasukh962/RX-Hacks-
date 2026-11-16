"""v2 endpoints. OpenAI is never called: tests patch llm.chat_json / llm.web_answer. All text is invented."""
import pytest
from fastapi.testclient import TestClient

from app import llm, v2
from app.main import app

client = TestClient(app)

AVS = """AFTER VISIT SUMMARY
Meloxicam 15 mg Tab
Take 1 tablet by mouth daily . Take with food
Cyclobenzaprine Status: Discontinued
START taking these medications
Cyclobenzaprine 10 mg Tab
Take 1 tablet by mouth 2 times a day as needed for muscle spasms"""
NOTE = """Progress Note
Assessment and plan: Low back pain.
Take meloxicam.
get new x-ray to rule out compression fracture
Agrees to go to ER if symptoms of cauda equina syndrome develop."""


@pytest.fixture
def case():
    r = client.post("/api/cases", json={"documents": [{"text": AVS, "type_hint": "after_visit_summary"},
                                                      {"text": NOTE, "type_hint": "clinical_note"}]})
    assert r.status_code == 200
    v2.reset()
    return r.json()


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)


def test_insights_without_llm_gives_safe_fallback(case):
    r = client.post(f"/api/cases/{case['case_id']}/insights").json()
    assert r["mode"] == "demo" and r["findings"] == [] and r["summary"]["en"] and r["summary"]["es"]


def test_insights_keeps_only_findings_with_exact_quotes(case, live, monkeypatch):
    avs, note = [d["id"] for d in case["documents"]]
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "summary_en": ["You were seen for low back pain."], "summary_es": ["Lo vieron por dolor de espalda."],
        "findings": [
            {"type": "within_document", "title_en": "t", "title_es": "t", "instruction_id": "",
             "quotes": [{"document_id": avs, "quote": "Cyclobenzaprine Status: Discontinued"},
                        {"document_id": avs, "quote": "START taking these medications"}]},
            {"type": "only_in_one", "title_en": "ER warning", "title_es": "t", "instruction_id": "nope",
             "quotes": [{"document_id": note, "quote": "go to ER if symptoms of cauda equina syndrome develop"}]},
            {"type": "only_in_one", "title_en": "invented", "title_es": "t", "instruction_id": "",
             "quotes": [{"document_id": note, "quote": "Take 3 tablets at bedtime"}]},
            {"type": "worded_differently", "title_en": "same doc twice", "title_es": "t", "instruction_id": "",
             "quotes": [{"document_id": avs, "quote": "Meloxicam 15 mg Tab"}, {"document_id": avs, "quote": "Take with food"}]},
        ]})
    r = client.post(f"/api/cases/{case['case_id']}/insights").json()
    assert r["mode"] == "live" and r["summary"]["en"] == ["You were seen for low back pain."]
    assert [f["type"] for f in r["findings"]] == ["within_document", "only_in_one"]
    assert r["findings"][1]["instruction_id"] is None  # unknown id dropped, finding kept


def test_insights_summary_with_invented_number_falls_back(case, live, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "summary_en": ["Take meloxicam 30 mg."], "summary_es": ["Tome 30 mg."], "findings": []})
    r = client.post(f"/api/cases/{case['case_id']}/insights").json()
    assert "30" not in " ".join(r["summary"]["en"])


def test_demo_altered_changes_only_the_note_copy(case):
    r = client.post(f"/api/cases/{case['case_id']}/demo-altered")
    assert r.status_code == 200
    alt = r.json()
    assert alt["case_id"] != case["case_id"] and alt["original_case_id"] == case["case_id"]
    note = next(d for d in alt["documents"] if d["type"] == "clinical_note")
    assert "Take meloxicam 15 mg twice daily." in note["text"]
    assert alt["altered"] == [{"document_id": note["id"], "text": "Take meloxicam 15 mg twice daily."}]
    orig_note = next(d for d in client.get(f"/api/cases/{case['case_id']}").json()["documents"] if d["type"] == "clinical_note")
    assert "twice daily" not in orig_note["text"]  # the original record is untouched
    assert client.post(f"/api/cases/{case['case_id']}/demo-altered").json()["case_id"] == alt["case_id"]  # cached


def test_demo_altered_refuses_when_no_rule_applies():
    plan = client.post("/api/cases", json={"demo_case_id": "demo-cornea-001"}).json()
    assert client.post(f"/api/cases/{plan['case_id']}/demo-altered").status_code == 422


def _chat(case, text, **kw):
    return client.post("/api/chat", json={"case_id": case["case_id"], "messages": [{"role": "user", "content": text}], **kw}).json()


def test_chat_urgent_short_circuits(case):
    r = _chat(case, "I have chest pain and trouble breathing")
    assert r["urgent"] is True and r["tier"] == "urgent" and "911" in r["answer"]


def test_chat_documents_answer_with_verified_quotes_and_sources(case, live, monkeypatch):
    avs = case["documents"][0]["id"]
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "answer": "Your summary says to take 1 tablet daily with food. Meloxicam is an NSAID.",
        "tier": "documents", "needs_web": False, "offer_email": False,
        "quotes": [{"document_id": avs, "quote": "Take 1 tablet by mouth daily . Take with food"},
                   {"document_id": avs, "quote": "not in the document"}],
        "fact_ids": ["meloxicam.what_it_does"]})
    r = _chat(case, "How do I take meloxicam?", level="simple")
    assert r["tier"] == "documents" and r["level"] == "simple" and len(r["citations"]) == 1
    assert any("medlineplus" in s["url"] for s in r["sources"])


def test_chat_invented_number_or_stop_advice_is_blocked(case, live, monkeypatch):
    for bad in ["Take 30 mg of meloxicam.", "You can stop taking meloxicam now."]:
        monkeypatch.setattr(llm, "chat_json", lambda *a, _b=bad, **k: {
            "answer": _b, "tier": "drug_reference", "needs_web": False, "offer_email": False, "quotes": [], "fact_ids": []})
        r = _chat(case, "question about meloxicam")
        assert r["answer"] != bad and "30 mg" not in r["answer"]


def test_chat_missed_dose_phrase_from_fact_sheet_is_allowed(case, live, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "answer": "If it is almost time for the next dose, skip the missed dose and keep your normal schedule.",
        "tier": "drug_reference", "needs_web": False, "offer_email": False, "quotes": [],
        "fact_ids": ["meloxicam.missed_dose"]})
    r = _chat(case, "What if I miss a dose of meloxicam?")
    assert "skip the missed dose" in r["answer"] and r["tier"] == "drug_reference"


def test_chat_web_fallback_returns_sources(case, live, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "answer": "Let me look that up.", "tier": "unclear", "needs_web": True, "offer_email": False,
        "quotes": [], "fact_ids": []})
    seen = {}
    def fake_web(question, instructions):
        seen["q"] = question
        return {"text": "Light exercise is usually fine.", "sources": [{"title": "Mayo Clinic", "url": "https://www.mayoclinic.org/x"}]}
    monkeypatch.setattr(llm, "web_answer", fake_web)
    r = _chat(case, "Can I play basketball while taking it?")
    assert r["tier"] == "web" and r["sources"][0]["url"].startswith("https://www.mayoclinic.org")
    assert seen["q"] == "Can I play basketball while taking it?"  # only the question goes to the web search


def test_email_rewrite_rejects_new_numbers(live, monkeypatch):
    body = {"body": "Hello, I have a question about my visit.", "note": "I take it once a day", "language": "en"}
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"body": "Hello, I take 2 tablets."})
    assert client.post("/api/email/rewrite", json=body).json()["body"] is None
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"body": "Hello, I take it once a day. Which is right?"})
    assert client.post("/api/email/rewrite", json=body).json()["body"].startswith("Hello")


def test_only_in_one_claim_dropped_when_medicine_is_named_in_other_document(live, monkeypatch):
    note = NOTE + "\nRelevant Medications\n Cyclobenzaprine (FLEXERIL) 10 mg Oral Tab"
    plan = client.post("/api/cases", json={"documents": [{"text": AVS, "type_hint": "after_visit_summary"},
                                                         {"text": note, "type_hint": "clinical_note"}]}).json()
    avs = plan["documents"][0]["id"]
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "summary_en": ["You were seen for low back pain."], "summary_es": ["Dolor de espalda."],
        "findings": [{"type": "only_in_one", "title_en": "Cyclobenzaprine isn't in the note", "title_es": "t",
                      "instruction_id": "", "quotes": [{"document_id": avs, "quote": "Cyclobenzaprine Status: Discontinued"}]}]})
    assert client.post(f"/api/cases/{plan['case_id']}/insights").json()["findings"] == []


def test_same_documents_give_same_insights(case, live, monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: (calls.append(1) if k.get("name") == "insights" else None) or {
        "summary_en": ["You were seen for low back pain."], "summary_es": ["Dolor de espalda."], "findings": []})
    first = client.post(f"/api/cases/{case['case_id']}/insights").json()
    again = client.post("/api/cases", json={"documents": [{"text": AVS, "type_hint": "after_visit_summary"},
                                                          {"text": NOTE, "type_hint": "clinical_note"}]}).json()
    second = client.post(f"/api/cases/{again['case_id']}/insights").json()
    assert len(calls) == 1 and second["summary"] == first["summary"] and second["case_id"] == again["case_id"]
