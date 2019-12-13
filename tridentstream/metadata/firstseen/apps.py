from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.firstseen"
    verbose_name = "First Seen Metadata"
    label = "metadata_firstseen"

    def ready(self):
        from .handler import FirstSeenMetadataHandlerPlugin  # NOQA
