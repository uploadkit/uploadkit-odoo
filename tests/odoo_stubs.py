"""Minimal Odoo stubs so addon modules can be imported without Odoo installed."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock


class UserError(Exception):
    """Stand-in for ``odoo.exceptions.UserError``."""


class AbstractModel:
    """Plain base so addon AbstractModel subclasses are normal Python classes."""


class TransientModel:
    """Plain base for TransientModel subclasses."""


class _Field:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


def install_odoo_stubs() -> MagicMock:
    """Register fake ``odoo`` packages in ``sys.modules`` and return a request mock."""
    if "odoo" in sys.modules and getattr(sys.modules["odoo"], "_uploadkit_stub", False):
        return sys.modules["odoo.http"].request  # type: ignore[attr-defined]

    odoo = types.ModuleType("odoo")
    odoo._uploadkit_stub = True  # type: ignore[attr-defined]

    exceptions = types.ModuleType("odoo.exceptions")
    exceptions.UserError = UserError  # type: ignore[attr-defined]

    models = types.ModuleType("odoo.models")
    models.AbstractModel = AbstractModel  # type: ignore[attr-defined]
    models.TransientModel = TransientModel  # type: ignore[attr-defined]

    fields = types.ModuleType("odoo.fields")
    fields.Char = _Field  # type: ignore[attr-defined]
    fields.Integer = _Field  # type: ignore[attr-defined]

    http = types.ModuleType("odoo.http")

    def route(*_a: Any, **_kw: Any):
        def decorator(fn):
            return fn

        return decorator

    class Controller:
        pass

    request = MagicMock(name="odoo.http.request")
    http.route = route  # type: ignore[attr-defined]
    http.Controller = Controller  # type: ignore[attr-defined]
    http.request = request  # type: ignore[attr-defined]

    odoo.exceptions = exceptions  # type: ignore[attr-defined]
    odoo.models = models  # type: ignore[attr-defined]
    odoo.fields = fields  # type: ignore[attr-defined]
    odoo.http = http  # type: ignore[attr-defined]

    sys.modules["odoo"] = odoo
    sys.modules["odoo.exceptions"] = exceptions
    sys.modules["odoo.models"] = models
    sys.modules["odoo.fields"] = fields
    sys.modules["odoo.http"] = http
    return request
