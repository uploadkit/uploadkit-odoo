from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    uploadkit_storage_provider = fields.Char(
        string="Storage provider factory",
        config_parameter="uploadkit.storage_provider",
        help="Dotted path to a callable that returns a StorageProvider "
        "(e.g. my_module.storage.get_provider).",
    )
    uploadkit_bucket = fields.Char(
        string="Upload bucket",
        config_parameter="uploadkit.bucket",
        help="Bucket / container name passed to StorageProvider.put.",
    )
    uploadkit_object_prefix = fields.Char(
        string="Object name prefix",
        config_parameter="uploadkit.object_prefix",
        help="Optional prefix prepended to object names (e.g. uploads/).",
    )
    uploadkit_max_size = fields.Integer(
        string="Max upload size (bytes)",
        config_parameter="uploadkit.max_size",
        default=10 * 1024 * 1024,
        help="Maximum file size in bytes for the default UploadPolicy.",
    )
