"""HTTP upload route for UploadKit."""

from __future__ import annotations

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from uploadkit import UploaderError
from uploadkit_odoo import json_error_response


class UploadkitController(http.Controller):
    @http.route(
        "/uploadkit/upload",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def upload(self, **kw):
        uploaded = kw.get("file") or request.httprequest.files.get("file")
        if not uploaded or not getattr(uploaded, "filename", None):
            return request.make_json_response(
                {"error": "MissingFile", "message": "Expected multipart field 'file'."},
                status=400,
            )

        object_name = kw.get("object_name") or None
        try:
            result = request.env["uploadkit.service"].upload(
                uploaded,
                object_name=object_name,
            )
        except UserError as exc:
            return request.make_json_response(
                {"error": "ImproperlyConfigured", "message": str(exc)},
                status=400,
            )
        except UploaderError as exc:
            return json_error_response(exc)

        return request.make_json_response(result)
