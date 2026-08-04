"""Odoo integration for UploadKit.

Owns request adapters and response helpers only.
Does not implement validators, policies, or storage.
"""

from uploadkit_odoo.adapters import as_uploadable
from uploadkit_odoo.responses import (
    ERROR_STATUS,
    error_payload,
    json_error_response,
    status_for_error,
)

__all__ = [
    "as_uploadable",
    "ERROR_STATUS",
    "status_for_error",
    "error_payload",
    "json_error_response",
]

__version__ = "0.1.0"
