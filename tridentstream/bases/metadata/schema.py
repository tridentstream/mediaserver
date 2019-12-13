from ...plugins import ImageCachePlugin
from unplugged import RelatedPluginField, ServicePlugin, Schema


class MetadataSchema(Schema):
    image_cache = RelatedPluginField(plugin_type=ImageCachePlugin)
    metadata_server = RelatedPluginField(
        plugin_type=ServicePlugin, traits=["metadata_server"]
    )
