import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.dbs.memory"
    verbose_name = "Memory Database Plugin"
    label = "db_memory"

    def ready(self):
        from .handler import MemoryDatabasePlugin  # NOQA
