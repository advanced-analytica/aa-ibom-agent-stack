"""Tests for chat file upload validation."""

from app.services.file_storage import classify_file, normalize_mime_type
from app.services.file_upload import FileUploadService

MB = 1024 * 1024


def test_normalize_mime_type_strips_parameters() -> None:
    assert normalize_mime_type("text/plain;charset=utf-8") == "text/plain"
    assert normalize_mime_type(" Text/Plain ; charset=utf-8") == "text/plain"


def test_validate_upload_accepts_browser_text_mime_with_charset() -> None:
    is_valid, error = FileUploadService.validate_upload("text/plain;charset=utf-8", 128)

    assert is_valid is True
    assert error is None


def test_validate_upload_allows_10mb_files() -> None:
    is_valid, error = FileUploadService.validate_upload("application/pdf", 10 * MB)

    assert is_valid is True
    assert error is None


def test_validate_upload_rejects_files_over_10mb() -> None:
    is_valid, error = FileUploadService.validate_upload("application/pdf", 10 * MB + 1)

    assert is_valid is False
    assert error == "File too large. Maximum size is 10MB."


def test_classify_file_uses_normalized_mime_type() -> None:
    assert classify_file("image/png;charset=utf-8", "image.png") == "image"
    assert classify_file("application/pdf;charset=utf-8", "document.pdf") == "pdf"
