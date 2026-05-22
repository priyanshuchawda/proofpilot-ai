from io import BytesIO

from reportlab.pdfgen import canvas

from app.ingestion.extractors import extract_pages


def test_extract_pages_reads_pdf_text_with_page_numbers() -> None:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, "ProofPilot PDF evidence page")
    pdf.showPage()
    pdf.save()

    pages = extract_pages("evidence.pdf", buffer.getvalue())

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "ProofPilot PDF evidence page" in pages[0].text
