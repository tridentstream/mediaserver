import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.dbs.lmdb"
    verbose_name = "LMDB Database Plugin"
    label = "db_lmdb"

    def ready(self):
        try:
            from .handler import LMDBDatabasePlugin  # NOQA
        except ImportError:
            logger.info("Unable to load the LMDB database plugin")
