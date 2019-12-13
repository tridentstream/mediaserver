import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.metadata.mal"
    verbose_name = "MAL Metadata"
    label = "metadata_mal"

    def ready(self):
        from .parser import MALMetadataParserPlugin  # NOQA

        try:
            from .handler import MALMetadataHandlerPlugin  # NOQA
        except ImportError:
            logger.warning(
                "Unable to load mal metadata plugin, please install malparser"
            )
