"""Grounding rules for LLM extraction (no API calls: verify() runs on canned LLM output)."""
from app.extract import locate_quote, verify
from app.schemas import Document

DOC = Document(id="note-1", type="clinical_note", title="n",
               text="PLAN\n1. Increase lisinopril to 20 mg by mouth   daily.\n"
                    "2. Avoid NSAIDs given kidney risk; use acetaminophen for pain.")


def _item(**kw):
    base = {"kind": "medication", "medication_name": None, "strength": None, "dose": None, "route": None,
            "frequency_per_day": None, "duration": None, "action": None, "refills": None, "quantity": None,
            "due": None, "quote": ""}
    return {**base, **kw}


def test_locate_quote_tolerates_whitespace_and_snaps_to_source():
    span = locate_quote("Increase lisinopril to 20 mg by mouth daily.", DOC.text)
    assert span == "Increase lisinopril to 20 mg by mouth   daily."
    assert span in DOC.text


def test_unverifiable_quote_is_dropped():
    kept, dropped, _ = verify([_item(medication_name="lisinopril", quote="Take lisinopril 40 mg twice daily.")], DOC)
    assert kept == [] and dropped == 1


def test_numbers_not_in_quote_become_unknown():
    kept, _, nulled = verify([_item(medication_name="lisinopril", strength="40 mg", frequency_per_day=2,
                                    quote="Increase lisinopril to 20 mg by mouth daily.")], DOC)
    assert kept[0]["strength"] is None and kept[0]["frequency_per_day"] is None and nulled == 2


def test_supported_numbers_are_kept():
    kept, _, nulled = verify([_item(medication_name="lisinopril", strength="20 mg", frequency_per_day=1,
                                    action="change", quote="Increase lisinopril to 20 mg by mouth daily.")], DOC)
    assert kept[0]["strength"] == "20 mg" and kept[0]["frequency_per_day"] == 1 and nulled == 0


def test_prescription_shorthand_frequency_is_supported():
    doc = Document(id="note-1", type="clinical_note", title="n", text="Amoxicillin 500 mg PO TID x 7 days.")
    kept, _, nulled = verify([_item(medication_name="amoxicillin", frequency_per_day=3,
                                    quote="Amoxicillin 500 mg PO TID x 7 days.")], doc)
    assert kept[0]["frequency_per_day"] == 3 and nulled == 0
    kept, _, _ = verify([_item(medication_name="amoxicillin", frequency_per_day=2,
                               quote="Amoxicillin 500 mg PO TID x 7 days.")], doc)
    assert kept[0]["frequency_per_day"] is None  # BID claimed, TID written -> unknown


def test_avoid_drug_class_mislabeled_as_lifestyle_is_promoted():
    kept, _, _ = verify([_item(kind="lifestyle", action="avoid",
                               quote="Avoid NSAIDs given kidney risk")], DOC)
    assert kept[0]["kind"] == "medication" and kept[0]["medication_name"].lower() == "nsaids"
