import pytest
from fastapi.testclient import TestClient

from app import classifier
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def ml_on(monkeypatch):
    monkeypatch.setenv("REXO_DISABLE_ML", "0")
    if not classifier.load():
        pytest.skip(f"classifier unavailable: {classifier.status()['error']}")
    yield
    client.post("/api/demo/reset")  # reload trained weights, undo live updates


def test_barrier_spanish_side_effect_and_stop():
    probs = classifier.predict_barrier("Las gotas me raspan el ojo y ya no las quiero usar")
    assert probs["side_effect"] >= 0.5 or probs["wants_to_stop"] >= 0.5


def test_teachback_ml_fills_gap_rules_cannot_parse():
    client.post("/api/cases", json={"demo_case_id": "demo-matching-003"})
    r = client.post("/api/teachback", json={
        "case_id": "demo-matching-003", "profile_id": "ml1", "instruction_id": "med-avs-1",
        "response_text": "1 tablet twice a day until I feel better"}).json()
    # rules parse the dose and frequency; the stop-early phrase is caught too
    assert "stop_negation" in r["labels"]
    assert r["pathway"] in ("rules", "both")
    assert 0.0 <= r["confidence"] <= 1.0


def test_correction_updates_model_live_and_reset_reverts():
    text = "Tengo que escoger entre comprar comida o comprar las gotas"
    target = ["cost"]
    before = classifier.predict_barrier(text)
    client.post("/api/cases", json={"demo_case_id": "demo-cornea-001"})
    b = client.post("/api/barrier", json={"case_id": "demo-cornea-001", "profile_id": "ml2", "text": text}).json()
    r = client.post("/api/feedback", json={"profile_id": "ml2", "kind": "label_correct",
                                           "payload": {"example_id": b["example_id"], "labels": target}}).json()
    assert r["model_updated"] is True
    after = classifier.predict_barrier(text)
    assert [l for l, p in after.items() if p >= 0.5] == target
    client.post("/api/demo/reset")
    assert classifier.predict_barrier(text) == pytest.approx(before, abs=1e-6)
