# uploadkit-odoo

[![CI](https://github.com/uploadkit/uploadkit-odoo/actions/workflows/ci.yml/badge.svg)](https://github.com/uploadkit/uploadkit-odoo/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/uploadkit/uploadkit-odoo/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![Odoo](https://img.shields.io/badge/odoo-17%20%7C%2018-purple)](addons/uploadkit_odoo)

Odoo integration for UploadKit.

## What problem does this solve?

Adapts Werkzeug/`FileStorage` uploads from Odoo controllers and maps UploadKit exceptions to JSON responses — without reimplementing validation or storage. An optional Odoo 17/18 addon wires settings and a thin upload service/HTTP route.

## When to use it

Use when an Odoo app uploads files through UploadKit Core (controllers or the `uploadkit.service` model).

## When not to use it

Do not put validators, policies, or storage implementations in this package. Supply your own `StorageProvider` (e.g. boto3 → AWS S3 or MinIO). Creating `ir.attachment` records after upload is left to your module.

## Installation

Requires **Python 3.10–3.12** (Odoo 17/18 host range) and **Odoo 17 or 18** for the addon.

```bash
pip install uploadkit-odoo uploadkit-security
```

```bash
uv add uploadkit-odoo uploadkit-security
```

```bash
poetry add uploadkit-odoo uploadkit-security
```

For S3/MinIO samples: `pip install boto3`.

### Python × Odoo support

| Python | Odoo |
|--------|------|
| 3.10–3.12 | Odoo 17, Odoo 18 |

Python 3.13+ will be added once Odoo officially supports it.

### Licenses

- PyPI package (`uploadkit-odoo`): **Apache-2.0**
- Odoo addon (`addons/uploadkit_odoo`): **LGPL-3**

## Library quick start (controller)

```python
from odoo import http
from odoo.http import request
from uploadkit import Uploader, UploadPolicy, UploaderError
from uploadkit_odoo import as_uploadable, json_error_response
from uploadkit_security import default_validators


def notify(result):
    ...


class MyController(http.Controller):
    @http.route("/my/upload", type="http", auth="user", methods=["POST"], csrf=True)
    def upload(self, **kw):
        storage = get_provider()  # your StorageProvider factory
        policy = UploadPolicy(
            max_size=5 * 1024 * 1024,
            allowed_extensions=frozenset({"png"}),
            allowed_mime_types=frozenset({"image/png"}),
            validators=default_validators(),
        )
        uploaded = kw.get("file")
        try:
            result = Uploader(policy, storage).upload(
                as_uploadable(uploaded),
                bucket="uploads",
                object_name=uploaded.filename,
                after_upload=notify,  # or a Celery-like task with .delay
            )
        except UploaderError as exc:
            return json_error_response(exc)
        return request.make_json_response(result.as_task_kwargs())
```

## After-upload

Library controllers can pass Core `after_upload` on `Uploader.upload` (sync callback or Celery-like `.delay`). The optional addon `uploadkit.service.upload()` returns `UploadResult.as_task_kwargs()` and does **not** accept a hook — call Core `Uploader` directly (as above), or enqueue work from the returned dict. Full semantics: [uploadkit Core README](https://github.com/uploadkit/uploadkit#after-upload-hooks).

## Storage provider (AWS S3 or MinIO)

Same class for both backends — omit `endpoint_url` for AWS, set it for MinIO:

```python
# my_module/storage.py
import boto3
from botocore.client import Config
from odoo.tools import config


class Boto3S3Storage:
    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ) -> None:
        kwargs: dict = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
            "config": Config(signature_version="s3v4"),
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self.client = boto3.client(**kwargs)

    def put(self, *, bucket, object_name, body, content_type):
        resp = self.client.put_object(
            Bucket=bucket,
            Key=object_name,
            Body=body,
            ContentType=content_type,
        )
        return resp.get("ETag")


def get_provider():
    """Factory used by uploadkit.storage_provider config parameter."""
    return Boto3S3Storage(
        access_key=config.get("uploadkit_access_key", ""),
        secret_key=config.get("uploadkit_secret_key", ""),
        region=config.get("uploadkit_region", "us-east-1"),
        endpoint_url=config.get("uploadkit_endpoint_url") or None,
    )
```

## Odoo addon

1. Add this repo’s `addons/` directory to Odoo `addons_path`.
2. `pip install uploadkit-odoo uploadkit-security` (and your storage deps).
3. Install **UploadKit** in Apps.
4. Configure under **Settings → UploadKit**:
   - Storage provider factory (dotted path, e.g. `my_module.storage.get_provider`)
   - Upload bucket
   - Optional object name prefix and max size

### Service API

```python
result = env["uploadkit.service"].upload(file_storage, object_name="docs/a.pdf")
# result is UploadResult.as_task_kwargs() — no after_upload parameter
# Enqueue from the dict, or call Uploader.upload(..., after_upload=...) yourself
```

### HTTP route

`POST /uploadkit/upload` (`auth=user`, CSRF) with multipart field `file` (optional `object_name`). Returns JSON success payload or the standard UploadKit error shape.

After a successful upload you may create an `ir.attachment` yourself (e.g. `type='url'` pointing at your object URL). This package does not store into `ir.attachment`.

## Architecture

Thin adapters over UploadKit Core. Odoo multipart uploads are Werkzeug `FileStorage`; `as_uploadable` wraps them for `Uploader`.

## Public API (library)

| Symbol | Kind |
|--------|------|
| `as_uploadable` | Public |
| `json_error_response` / `status_for_error` / `error_payload` | Public |

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
