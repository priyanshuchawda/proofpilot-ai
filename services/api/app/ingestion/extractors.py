from io import BytesIO
from pathlib import PurePath

from pypdf import PdfReader

from app.ingestion.chunking import SourcePage


class TextExtractionError(ValueError):
    pass


def extract_pages(filename: str, content: bytes) -> list[SourcePage]:
    extension = PurePath(filename).suffix.lower()
    if extension in {".txt", ".md", ".markdown"}:
        return [SourcePage(page_number=None, text=content.decode("utf-8"))]
    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        return [
            SourcePage(page_number=index + 1, text=page.extract_text() or "")
            for index, page in enumerate(reader.pages)
        ]
    raise TextExtractionError("Unsupported document type.")
