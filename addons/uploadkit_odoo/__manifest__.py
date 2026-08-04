{
    "name": "UploadKit",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Secure file uploads via UploadKit Core (Odoo 17 and 18)",
    "description": """
Thin Odoo wiring for UploadKit: settings, upload service, and HTTP upload route.
Does not implement validators, policies, or storage providers.
Requires the uploadkit-odoo Python package (pip install uploadkit-odoo).
    """,
    "author": "UploadKit",
    "website": "https://github.com/uploadkit/uploadkit-odoo",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
