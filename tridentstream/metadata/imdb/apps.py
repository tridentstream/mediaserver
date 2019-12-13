import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.imdb"
    verbose_name = "IMDB Metadata"
    label = "metadata_imdb"

    def ready(self):
        from .parser import IMDBMetadataParserPlugin  # NOQA

        try:
            from .handler import IMDBMetadataHandlerPlugin  # NOQA
        except ImportError:
            logger.warning(
                "Unable to load mal metadata plugin, please install imdbparser"
            )
