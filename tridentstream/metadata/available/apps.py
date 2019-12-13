from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.available"
    verbose_name = "Available Metadata"
    label = "metadata_available"

    def ready(self):
        from .handler import AvailableMetadataHandlerPlugin  # NOQA
