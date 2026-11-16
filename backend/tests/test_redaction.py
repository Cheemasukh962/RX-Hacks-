"""Portal-export redaction. All names and numbers here are invented."""
from app import ingest

PORTAL = """Date printed: 11/15/2026
Health Plan Member name: Jordan Q Testperson
Date of birth: 04/05/1999
MRN: 998877665544
Office Visit - Aug 17, 2026
with ALICE BEATRICE EXAMPLEDOC MD at Adult/family Medicine
Jordan Q. Testperson   MRN: 998877665544
CEID: Z99-AAAA-BBBB-CCCC
 ADULT/FAMILY MEDICINE   916-555-0100
You saw ALICE BEATRICE EXAMPLEDOC MD on Monday August 17, 2026.
PT Office Visit with CARL DEMO PT
PHYSICAL THERAPY SPORTS MED
123 J STREET
SACRAMENTO CA 95814-2326
https://portal.example.org/app/visits/past-details?csn=WP-SECRETTOKEN123
Meloxicam 15 mg Tab
Take 1 tablet by mouth daily . Take with food
Started by: ALICE
BEATRICE EXAMPLEDOC MD
Jordan Testperson, age 20 Y, presents with the following concerns.
CHRONIC LOW BACK PAIN
NAIL DYSTROPHY
ALLERGIC RHINITIS
ASTHMA, UNSPECIFIED
OBESITY, BMI 35-39.9, ADULT
PREDIABETES
RIGHT ANKLE SPRAIN
 Relevant Medications
Assessment and plan: Low back pain.
Take meloxicam.
Agrees to go to ER if symptoms of cauda equina syndrome develop.
"""


def test_portal_identifiers_removed():
    out, n = ingest.redact(PORTAL)
    for secret in ["Jordan", "Testperson", "04/05/1999", "998877665544", "Z99-AAAA-BBBB-CCCC",
                   "EXAMPLEDOC", "BEATRICE", "CARL DEMO", "916-555-0100", "123 J STREET",
                   "95814", "SECRETTOKEN123"]:
        assert secret not in out, secret
    assert n >= 10


def test_problem_list_block_removed_but_care_instructions_kept():
    out, _ = ingest.redact(PORTAL)
    for dx in ["NAIL DYSTROPHY", "OBESITY", "PREDIABETES", "ASTHMA"]:
        assert dx not in out, dx
    for kept in ["Meloxicam 15 mg Tab", "Take 1 tablet by mouth daily . Take with food", "Take meloxicam.",
                 "Agrees to go to ER if symptoms of cauda equina syndrome develop.", "Low back pain.",
                 "Office Visit - Aug 17, 2026"]:
        assert kept in out, kept


def test_simple_label_lines_still_redacted_and_idempotent():
    text = "Patient Name: Alex Sample\nDOB: 01/01/1970\nMRN: 00000001\nTake 1 drop four times daily."
    out, n = ingest.redact(text)
    assert "Alex" not in out and "01/01/1970" not in out and "00000001" not in out
    assert "Take 1 drop four times daily." in out and n >= 3
    again, n2 = ingest.redact(out)
    assert again == out and n2 == 0
