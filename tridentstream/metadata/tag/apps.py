from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.tag"
    verbose_name = "Tag Metadata"
    label = "metadata_tag"

    def ready(self):
        from .handler import TagMetadataHandlerPlugin  # NOQA
        from .tag import TagTagPlugin  # NOQA
