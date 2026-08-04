"""Thin UploadKit service — resolves config and calls Core Uploader."""

from __future__ import annotations

import importlib
from typing import Any

from odoo import models
from odoo.exceptions import UserError

from uploadkit import UploadPolicy, Uploader
from uploadkit_odoo import as_uploadable


def _import_string(dotted_path: str) -> Any:
    module_path, _, attr = dotted_path.rpartition(".")
    if not module_path or not attr:
        raise ImportError(f"Invalid dotted path: {dotted_path!r}")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


class UploadkitService(models.AbstractModel):
    _name = "uploadkit.service"
    _description = "UploadKit upload service"

    def _get_param(self, key: str, default: str | None = None) -> str | None:
        value = self.env["ir.config_parameter"].sudo().get_param(key, default=default)
        if value is None or value == "":
            return default
        return value

    def get_storage_provider(self):
        """Resolve ``uploadkit.storage_provider`` config parameter."""
        path = self._get_param("uploadkit.storage_provider")
        if not path:
            raise UserError(
                "Set UploadKit storage provider "
                "(Settings → UploadKit → Storage provider factory)."
            )
        factory = _import_string(path)
        if not callable(factory):
            raise UserError(
                "uploadkit.storage_provider must be a callable factory."
            )
        return factory()

    def _build_policy(self) -> UploadPolicy:
        max_size_raw = self._get_param("uploadkit.max_size", "10485760")
        try:
            max_size = int(max_size_raw) if max_size_raw else None
        except ValueError as exc:
            raise UserError("uploadkit.max_size must be an integer.") from exc

        validators: tuple = ()
        try:
            from uploadkit_security import default_validators

            validators = tuple(default_validators())
        except ImportError:
            pass

        return UploadPolicy(max_size=max_size, validators=validators)

    def upload(self, file_storage, *, object_name: str | None = None) -> dict:
        """Upload ``file_storage`` via UploadKit Core.

        Returns a dict of ``UploadResult`` fields (``as_task_kwargs``).
        Raises ``UploaderError`` on validation/storage failure, or
        ``UserError`` when settings are missing.
        """
        storage = self.get_storage_provider()
        bucket = self._get_param("uploadkit.bucket")
        if not bucket:
            raise UserError(
                "Set UploadKit bucket (Settings → UploadKit → Upload bucket)."
            )

        prefix = self._get_param("uploadkit.object_prefix") or ""
        name = object_name or getattr(file_storage, "filename", None) or "upload"
        if prefix and not name.startswith(prefix):
            name = f"{prefix}{name}"

        policy = self._build_policy()
        result = Uploader(policy, storage).upload(
            as_uploadable(file_storage),
            bucket=bucket,
            object_name=name,
        )
        return result.as_task_kwargs()
