# Contributing

```bash
pip install -e ../uploadkit -e ../uploadkit-testing -e ../uploadkit-security
pip install -e ".[dev]"
pytest
```

Library tests cover `src/uploadkit_odoo`. Addon tests in `tests/test_odoo_addon.py` use lightweight Odoo stubs (no Odoo install required).

Do not add validators, policies, or storage implementations here.
The Odoo addon under `addons/uploadkit_odoo/` only wires Core via settings and thin helpers.
