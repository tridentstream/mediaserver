from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.store"
    verbose_name = "Store Service"
    label = "services_store"

    def ready(self):
        from .handler import StoreService  # NOQA
