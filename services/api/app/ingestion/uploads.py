import re
from pathlib import PurePath

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}

TEXT_MIME_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}


class UnsupportedUploadError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


def safe_storage_name(filename: str, *, content_hash: str) -> str:
    original_name = PurePath(filename.replace("\\", "/")).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name).strip("._")
    if not safe_name:
        safe_name = "document"
    return f"{content_hash}_{safe_name}"


def validate_upload_metadata(*, filename: str, content_type: str | None, size: int) -> None:
    if size > MAX_UPLOAD_BYTES:
        raise UploadTooLargeError(f"Uploads are limited to {MAX_UPLOAD_BYTES} bytes.")

    extension = PurePath(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedUploadError("Only PDF, TXT, and Markdown uploads are supported.")

    if extension == ".pdf" and content_type != "application/pdf":
        raise UnsupportedUploadError("PDF uploads must use application/pdf.")

    if extension in {".txt", ".md", ".markdown"} and content_type not in TEXT_MIME_TYPES:
        raise UnsupportedUploadError("Text uploads must use a supported text MIME type.")
