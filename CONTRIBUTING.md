# Contributing

```bash
pip install -e ../uploadkit -e ../uploadkit-testing -e ../uploadkit-security
pip install -e ".[dev]"
pytest
```

Do not add validators, policies, or storage implementations here.
The Odoo addon under `addons/uploadkit_odoo/` only wires Core via settings and thin helpers.
