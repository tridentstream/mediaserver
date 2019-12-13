from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.history"
    verbose_name = "History Metadata"
    label = "metadata_history"

    def ready(self):
        from .handler import HistoryMetadataHandlerPlugin  # NOQA
        from .history import HistoryHistoryPlugin  # NOQA
