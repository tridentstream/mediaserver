from unplugged import RelatedPluginField, Schema, ServicePlugin

from ...plugins import ImageCachePlugin


class MetadataSchema(Schema):
    image_cache = RelatedPluginField(plugin_type=ImageCachePlugin)
    metadata_server = RelatedPluginField(
        plugin_type=ServicePlugin, traits=["metadata_server"]
    )
