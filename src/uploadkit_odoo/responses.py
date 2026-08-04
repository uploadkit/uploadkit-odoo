"""Map UploadKit exceptions to HTTP status / Werkzeug JSON responses."""

from __future__ import annotations

import json
from typing import Any

from werkzeug.wrappers import Response

from uploadkit import (
    EmptyFile,
    FileTooLarge,
    InvalidExtension,
    InvalidFileContent,
    InvalidFileName,
    InvalidMimeType,
    UploadFailed,
    UploaderError,
)

# Default HTTP status codes for UploaderError subclasses.
ERROR_STATUS: dict[type[UploaderError], int] = {
    FileTooLarge: 413,
    EmptyFile: 400,
    InvalidExtension: 400,
    InvalidMimeType: 400,
    InvalidFileName: 400,
    InvalidFileContent: 400,
    UploadFailed: 502,
}


def status_for_error(exc: UploaderError) -> int:
    """Return an HTTP status code for ``exc``."""
    for exc_type, status in ERROR_STATUS.items():
        if isinstance(exc, exc_type):
            return status
    return 400


def error_payload(exc: UploaderError) -> dict[str, Any]:
    """JSON-serializable error body."""
    return {
        "error": type(exc).__name__,
        "message": str(exc),
    }


def json_error_response(exc: UploaderError) -> Response:
    """Build a Werkzeug ``Response`` for an ``UploaderError``."""
    return Response(
        json.dumps(error_payload(exc)),
        status=status_for_error(exc),
        mimetype="application/json",
    )
