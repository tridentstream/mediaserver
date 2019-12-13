import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.dbs.leveldb"
    verbose_name = "LevelDB Database Plugin"
    label = "db_leveldb"

    def ready(self):
        try:
            from .handler import LevelDBDatabasePlugin  # NOQA
        except ImportError:
            logger.info("Unable to load the LevelDB database plugin")
