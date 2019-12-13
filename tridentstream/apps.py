import logging

from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream"
    verbose_name = "Tridentstream"

    def ready(self):
        from .eventtrack import register_signals

        register_signals()
