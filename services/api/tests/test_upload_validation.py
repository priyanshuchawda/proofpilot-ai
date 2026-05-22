import pytest

from app.ingestion.uploads import (
    MAX_UPLOAD_BYTES,
    UnsupportedUploadError,
    UploadTooLargeError,
    safe_storage_name,
    validate_upload_metadata,
)


def test_safe_storage_name_blocks_path_traversal() -> None:
    stored_name = safe_storage_name("../../secret.env", content_hash="abc123")

    assert stored_name == "abc123_secret.env"
    assert ".." not in stored_name
    assert "/" not in stored_name
    assert "\\" not in stored_name


def test_validate_upload_metadata_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedUploadError):
        validate_upload_metadata(
            filename="malware.exe", content_type="application/octet-stream", size=10
        )


def test_validate_upload_metadata_rejects_oversized_files() -> None:
    with pytest.raises(UploadTooLargeError):
        validate_upload_metadata(
            filename="large.md",
            content_type="text/markdown",
            size=MAX_UPLOAD_BYTES + 1,
        )
