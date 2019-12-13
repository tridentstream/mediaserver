from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.embedded"
    verbose_name = "Embedded Metadata"
    label = "metadata_embedded"

    def ready(self):
        from .handler import EmbeddedMetadataHandlerPlugin  # NOQA
