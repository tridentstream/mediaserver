import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.dbs.shelve"
    verbose_name = "Shelve Database Plugin"
    label = "db_shelve"

    def ready(self):
        from .handler import ShelfDatabasePlugin  # NOQA
