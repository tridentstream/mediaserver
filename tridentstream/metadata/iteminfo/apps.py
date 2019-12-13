from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.iteminfo"
    verbose_name = "ItemInfo Metadata"
    label = "metadata_iteminfo"

    def ready(self):
        from .handler import ItemInfoMetadataHandlerPlugin  # NOQA
