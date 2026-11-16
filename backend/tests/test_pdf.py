from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_pdf(lines: list[str]) -> bytes:
    """A minimal one-page text PDF (invented content), built by hand so tests need no PDF writer."""
    ops = "BT /F1 11 Tf 50 750 Td 14 TL " + " ".join(
        "(" + l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") '" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(ops)} >>\nstream\n{ops}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def test_pdf_text_is_extracted_and_redacted():
    pdf = make_pdf(["Member name: Jordan Q Testperson", "MRN: 998877665544",
                    "Meloxicam 15 mg Tab", "Take 1 tablet by mouth daily. Take with food"])
    r = client.post("/api/ingest/pdf", files={"file": ("visit.pdf", pdf, "application/pdf")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "Take 1 tablet by mouth daily" in body["text"]
    assert "Testperson" not in body["text"] and "998877665544" not in body["text"]
    assert body["pages"] == 1 and body["redacted_count"] >= 2 and body["mode"] in ("live", "demo")


def test_non_pdf_and_empty_pdf_rejected_with_readable_message():
    r = client.post("/api/ingest/pdf", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 422 and "not a PDF" in r.json()["detail"]
    r = client.post("/api/ingest/pdf", files={"file": ("x.pdf", make_pdf([]), "application/pdf")})
    assert r.status_code == 422 and "paste the text" in r.json()["detail"]
