"""Unit tests for the Odoo addon (service + HTTP controller) without Odoo installed."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from werkzeug.datastructures import FileStorage

from uploadkit import InvalidExtension, UploadFailed
from uploadkit_testing import FakeStorageProvider

from tests.odoo_stubs import UserError, install_odoo_stubs

ADDON_ROOT = Path(__file__).resolve().parents[1] / "addons" / "uploadkit_odoo"


def _load(name: str, relative: str):
    path = ADDON_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def request_mock():
    return install_odoo_stubs()


@pytest.fixture(scope="module")
def service_mod(request_mock):
    return _load("uploadkit_odoo_addon_service", "models/uploadkit_service.py")


@pytest.fixture(scope="module")
def controller_mod(request_mock):
    return _load("uploadkit_odoo_addon_controller", "controllers/upload.py")


@pytest.fixture(scope="module")
def settings_mod(request_mock):
    return _load("uploadkit_odoo_addon_settings", "models/res_config_settings.py")


def _make_file_storage(
    filename: str,
    data: bytes,
    content_type: str = "text/plain",
) -> FileStorage:
    return FileStorage(
        stream=io.BytesIO(data),
        filename=filename,
        content_type=content_type,
        content_length=len(data),
    )


def _service(service_mod, params: dict[str, str | None]):
    """Build an UploadkitService instance with a fake ir.config_parameter store."""
    svc = service_mod.UploadkitService()
    param_model = MagicMock()

    def get_param(key: str, default=None):
        if key in params:
            return params[key]
        return default

    param_model.sudo.return_value.get_param.side_effect = get_param
    env = MagicMock()
    env.__getitem__.side_effect = lambda name: param_model if name == "ir.config_parameter" else MagicMock()
    svc.env = env
    return svc


def make_fake_storage() -> FakeStorageProvider:
    return FakeStorageProvider(etag="addon-etag")


def test_settings_module_defines_fields(settings_mod) -> None:
    cls = settings_mod.ResConfigSettings
    assert cls._inherit == "res.config.settings"
    assert hasattr(cls, "uploadkit_storage_provider")
    assert hasattr(cls, "uploadkit_bucket")
    assert hasattr(cls, "uploadkit_object_prefix")
    assert hasattr(cls, "uploadkit_max_size")


def test_import_string_invalid(service_mod) -> None:
    with pytest.raises(ImportError, match="Invalid dotted path"):
        service_mod._import_string("nosep")


def test_get_storage_provider_missing(service_mod) -> None:
    svc = _service(service_mod, {"uploadkit.storage_provider": None})
    with pytest.raises(UserError, match="storage provider"):
        svc.get_storage_provider()


def test_get_storage_provider_empty_string(service_mod) -> None:
    svc = _service(service_mod, {"uploadkit.storage_provider": ""})
    with pytest.raises(UserError, match="storage provider"):
        svc.get_storage_provider()


def test_get_storage_provider_non_callable(service_mod, monkeypatch) -> None:
    import types

    mod = types.ModuleType("tests._addon_factory_mod")
    mod.VALUE = "not-a-factory"  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "tests._addon_factory_mod", mod)

    svc = _service(
        service_mod,
        {"uploadkit.storage_provider": "tests._addon_factory_mod.VALUE"},
    )
    with pytest.raises(UserError, match="callable factory"):
        svc.get_storage_provider()


def test_get_storage_provider_ok(service_mod) -> None:
    svc = _service(
        service_mod,
        {"uploadkit.storage_provider": "tests.test_odoo_addon.make_fake_storage"},
    )
    provider = svc.get_storage_provider()
    assert (
        provider.put(
            bucket="b",
            object_name="o",
            body=b"x",
            content_type="text/plain",
        )
        == "addon-etag"
    )


def test_build_policy_invalid_max_size(service_mod) -> None:
    svc = _service(service_mod, {"uploadkit.max_size": "not-int"})
    with pytest.raises(UserError, match="max_size"):
        svc._build_policy()


def test_build_policy_with_security(service_mod) -> None:
    svc = _service(service_mod, {"uploadkit.max_size": "2048"})
    policy = svc._build_policy()
    assert policy.max_size == 2048
    assert len(policy.validators) > 0


def test_build_policy_without_security(service_mod, monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "uploadkit_security" or name.startswith("uploadkit_security."):
            raise ImportError("no security")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    svc = _service(service_mod, {"uploadkit.max_size": "1024"})
    policy = svc._build_policy()
    assert policy.max_size == 1024
    assert policy.validators == ()


def test_upload_missing_bucket(service_mod) -> None:
    svc = _service(
        service_mod,
        {
            "uploadkit.storage_provider": "tests.test_odoo_addon.make_fake_storage",
            "uploadkit.bucket": None,
            "uploadkit.max_size": "10485760",
        },
    )
    with pytest.raises(UserError, match="bucket"):
        svc.upload(_make_file_storage("a.txt", b"hi"))


def test_upload_success_applies_prefix(service_mod) -> None:
    svc = _service(
        service_mod,
        {
            "uploadkit.storage_provider": "tests.test_odoo_addon.make_fake_storage",
            "uploadkit.bucket": "uploads",
            "uploadkit.object_prefix": "docs/",
            "uploadkit.max_size": "10485760",
        },
    )
    result = svc.upload(_make_file_storage("a.txt", b"hello world"))
    assert result["bucket"] == "uploads"
    assert result["object_name"] == "docs/a.txt"
    assert result["original_name"] == "a.txt"
    assert result["etag"] == "addon-etag"


def test_upload_explicit_object_name_skips_duplicate_prefix(service_mod) -> None:
    svc = _service(
        service_mod,
        {
            "uploadkit.storage_provider": "tests.test_odoo_addon.make_fake_storage",
            "uploadkit.bucket": "uploads",
            "uploadkit.object_prefix": "docs/",
            "uploadkit.max_size": "10485760",
        },
    )
    result = svc.upload(
        _make_file_storage("a.txt", b"hello world"),
        object_name="docs/already.txt",
    )
    assert result["object_name"] == "docs/already.txt"


def test_upload_default_name_when_filename_missing(service_mod) -> None:
    svc = _service(
        service_mod,
        {
            "uploadkit.storage_provider": "tests.test_odoo_addon.make_fake_storage",
            "uploadkit.bucket": "uploads",
            "uploadkit.max_size": "10485760",
        },
    )
    # Bypass security validators so we only assert object-name fallback.
    svc._build_policy = lambda: __import__("uploadkit", fromlist=["UploadPolicy"]).UploadPolicy(
        validators=()
    )
    uploaded = FileStorage(
        stream=io.BytesIO(b"x"),
        filename=None,
        content_type="text/plain",
        content_length=1,
    )
    result = svc.upload(uploaded)
    assert result["object_name"] == "upload"


def test_controller_missing_file(controller_mod, request_mock) -> None:
    request_mock.httprequest.files.get.return_value = None
    request_mock.make_json_response.side_effect = lambda body, status=200: (body, status)

    ctrl = controller_mod.UploadkitController()
    body, status = ctrl.upload()
    assert status == 400
    assert body["error"] == "MissingFile"


def test_controller_missing_filename(controller_mod, request_mock) -> None:
    request_mock.make_json_response.side_effect = lambda body, status=200: (body, status)
    uploaded = FileStorage(stream=io.BytesIO(b"x"), filename=None)

    ctrl = controller_mod.UploadkitController()
    body, status = ctrl.upload(file=uploaded)
    assert status == 400
    assert body["error"] == "MissingFile"


def test_controller_user_error(controller_mod, request_mock) -> None:
    request_mock.make_json_response.side_effect = lambda body, status=200: (body, status)
    service = MagicMock()
    service.upload.side_effect = UserError("not configured")
    request_mock.env = {"uploadkit.service": service}

    ctrl = controller_mod.UploadkitController()
    uploaded = _make_file_storage("a.txt", b"hi")
    body, status = ctrl.upload(file=uploaded)
    assert status == 400
    assert body["error"] == "ImproperlyConfigured"
    assert "not configured" in body["message"]


def test_controller_uploader_error(controller_mod, request_mock) -> None:
    service = MagicMock()
    service.upload.side_effect = InvalidExtension("bad ext")
    request_mock.env = {"uploadkit.service": service}

    ctrl = controller_mod.UploadkitController()
    uploaded = _make_file_storage("a.exe", b"hi")
    response = ctrl.upload(file=uploaded)
    assert response.status_code == 400
    payload = json.loads(response.get_data(as_text=True))
    assert payload["error"] == "InvalidExtension"


def test_controller_upload_failed(controller_mod, request_mock) -> None:
    service = MagicMock()
    service.upload.side_effect = UploadFailed("down")
    request_mock.env = {"uploadkit.service": service}

    ctrl = controller_mod.UploadkitController()
    response = ctrl.upload(file=_make_file_storage("a.txt", b"hi"))
    assert response.status_code == 502


def test_controller_success(controller_mod, request_mock) -> None:
    request_mock.make_json_response.side_effect = lambda body, status=200: (body, status)
    service = MagicMock()
    service.upload.return_value = {
        "bucket": "uploads",
        "object_name": "a.txt",
        "etag": "e1",
    }
    request_mock.env = {"uploadkit.service": service}

    ctrl = controller_mod.UploadkitController()
    body, status = ctrl.upload(file=_make_file_storage("a.txt", b"hi"), object_name="a.txt")
    assert status == 200
    assert body["object_name"] == "a.txt"
    service.upload.assert_called_once()
    args, kwargs = service.upload.call_args
    assert kwargs.get("object_name") == "a.txt"
