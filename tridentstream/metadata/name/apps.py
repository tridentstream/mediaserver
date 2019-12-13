import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.name"
    verbose_name = "Name Metadata"
    label = "metadata_name"

    def ready(self):
        from .handler import NameMetadataHandlerPlugin  # NOQA
