from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.thetvdb"
    verbose_name = "The TVDB Metadata"
    label = "metadata_thetvdb"

    def ready(self):
        try:
            from .handler import TheTVDBMetadataHandlerPlugin  # NOQA
        except ImportError:
            pass
