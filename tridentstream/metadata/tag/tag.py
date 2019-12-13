import logging

from django.contrib.contenttypes.models import ContentType
from unplugged import RelatedPluginField, Schema

from ...plugins import MetadataHandlerPlugin, TagPlugin

logger = logging.getLogger(__name__)


class TagSchema(Schema):
    tag_metadata = RelatedPluginField(plugin_type=MetadataHandlerPlugin, traits=["tag"])


class TagTagPlugin(TagPlugin):
    plugin_name = "tag"
    config_schema = TagSchema

    def __init__(self, config):
        self.tag = config["tag_metadata"]

    def tag_listingitem(self, config, user, listingitem, tag_name):
        level_config = config.get("level", {})

        for metadata_handler in level_config.get("metadata_handlers", []):
            if not metadata_handler.linkable:
                continue

            for metadata in listingitem.get_metadata(metadata_handler.plugin_name):
                content_type = ContentType.objects.get_for_model(metadata)

                try:
                    metadata_link = self.tag.metadata_link_model.objects.get(
                        user=user,
                        tag_name=tag_name,
                        object_id=metadata.pk,
                        content_type=content_type,
                    )
                except self.tag.metadata_link_model.DoesNotExist:
                    metadata_link = self.tag.metadata_link_model.objects.create(
                        user=user, tag_name=tag_name, metadata=metadata
                    )

                self.tag.listing_item_relation_model.objects.get_or_create(
                    metadata=metadata_link, listingitem=listingitem, user=user
                )

    def untag_listingitem(self, config, user, listingitem, tag_name):
        level_config = config.get("level", {})

        for metadata_handler in level_config.get("metadata_handlers", []):
            if not metadata_handler.linkable:
                continue

            for metadata in listingitem.get_metadata(metadata_handler.plugin_name):
                content_type = ContentType.objects.get_for_model(metadata)
                self.tag.metadata_link_model.objects.filter(
                    user=user,
                    tag_name=tag_name,
                    object_id=metadata.pk,
                    content_type=content_type,
                ).delete()
