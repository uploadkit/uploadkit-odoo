from __future__ import annotations

import io
import json

import pytest
from werkzeug.datastructures import FileStorage

from uploadkit import (
    EmptyFile,
    FileTooLarge,
    InvalidExtension,
    InvalidFileContent,
    InvalidFileName,
    InvalidMimeType,
    UploadFailed,
    UploadPolicy,
    Uploader,
    UploaderError,
)
from uploadkit_odoo import (
    as_uploadable,
    error_payload,
    json_error_response,
    status_for_error,
)
from uploadkit_security import default_validators
from uploadkit_testing import FakeStorageProvider


def _make_file_storage(
    filename: str,
    data: bytes,
    content_type: str = "text/plain",
    *,
    content_length: int | None = None,
) -> FileStorage:
    stream = io.BytesIO(data)
    return FileStorage(
        stream=stream,
        filename=filename,
        content_type=content_type,
        content_length=content_length if content_length is not None else len(data),
    )


def test_as_uploadable_round_trip() -> None:
    uploaded = _make_file_storage("hello.txt", b"hello")
    file = as_uploadable(uploaded)
    assert file.name == "hello.txt"
    assert file.size == 5
    assert file.content_type == "text/plain"
    assert file.read() == b"hello"


def test_as_uploadable_seek_tell() -> None:
    uploaded = _make_file_storage("seek.txt", b"abcdef")
    file = as_uploadable(uploaded)
    assert file.read(2) == b"ab"
    assert file.tell() == 2
    file.seek(0)
    assert file.tell() == 0
    assert file.read() == b"abcdef"


def test_as_uploadable_none_metadata() -> None:
    stream = io.BytesIO(b"x")
    uploaded = FileStorage(stream=stream, filename=None, content_type=None)
    file = as_uploadable(uploaded)
    assert file.name is None
    # Werkzeug may leave content_length unset (None) or as 0 depending on version.
    assert file.size in (None, 0)
    assert file.content_type is None
    assert file.read() == b"x"


def test_upload_with_file_storage() -> None:
    storage = FakeStorageProvider()
    policy = UploadPolicy(
        max_size=1024,
        allowed_extensions=frozenset({"txt"}),
        allowed_mime_types=frozenset({"text/plain"}),
        validators=default_validators(),
    )
    uploaded = _make_file_storage("note.txt", b"hello world")
    result = Uploader(policy, storage).upload(
        as_uploadable(uploaded),
        bucket="uploads",
        object_name="note.txt",
    )
    assert result.original_name == "note.txt"
    assert result.sha256 is not None
    assert len(storage.objects) == 1


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (FileTooLarge("too big"), 413),
        (EmptyFile("empty"), 400),
        (InvalidExtension("bad ext"), 400),
        (InvalidMimeType("bad mime"), 400),
        (InvalidFileName("bad name"), 400),
        (InvalidFileContent("bad content"), 400),
        (UploadFailed("storage down"), 502),
        (UploaderError("generic"), 400),
    ],
)
def test_status_for_error_mapping(
    exc: UploaderError,
    expected_status: int,
) -> None:
    assert status_for_error(exc) == expected_status


def test_json_error_response() -> None:
    response = json_error_response(InvalidExtension("bad"))
    assert response.status_code == 400
    assert response.mimetype == "application/json"
    body = json.loads(response.get_data(as_text=True))
    assert body == error_payload(InvalidExtension("bad"))
    assert body["error"] == "InvalidExtension"


def test_json_error_response_file_too_large() -> None:
    response = json_error_response(FileTooLarge("too big"))
    assert response.status_code == 413
    assert error_payload(FileTooLarge("too big"))["error"] == "FileTooLarge"


def test_json_error_response_upload_failed() -> None:
    response = json_error_response(UploadFailed("down"))
    assert response.status_code == 502
