import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.indexers.whoosh"
    verbose_name = "Whoosh Indexer"
    label = "indexers_whoosh"

    def ready(self):
        try:
            from .handler import WhooshIndexerPlugin  # NOQA
        except ImportError:
            logger.warning("Unable to load whoosh index plugin, please install whoosh")
