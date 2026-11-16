"""Text-layer PDF → text (patient-portal exports have a text layer). Scanned PDFs are not OCR'd here."""
from __future__ import annotations

import io

MAX_BYTES = 15 * 1024 * 1024
MAX_PAGES = 40


class PdfError(ValueError):
    pass


def pdf_text(payload: bytes) -> tuple[str, int]:
    """Return (text, page_count). Raises PdfError with a patient-readable message."""
    if len(payload) > MAX_BYTES:
        raise PdfError("This PDF is too large. Please upload a file under 15 MB.")
    if not payload.startswith(b"%PDF"):
        raise PdfError("This file is not a PDF. Upload a PDF, or paste the text instead.")
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    try:
        reader = PdfReader(io.BytesIO(payload))
        if reader.is_encrypted:
            raise PdfError("This PDF is password-protected. Please paste the text instead.")
        pages = reader.pages[:MAX_PAGES]
        text = "\n".join((p.extract_text() or "") for p in pages)
    except PdfReadError:
        raise PdfError("This PDF could not be read. Please paste the text instead.")
    if len(text.strip()) < 20:
        raise PdfError("No text was found in this PDF (it may be a scan). Please paste the text instead.")
    return text, len(reader.pages)
