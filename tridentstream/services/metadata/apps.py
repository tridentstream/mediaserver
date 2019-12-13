from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.metadata"
    verbose_name = "Metadata Service"
    label = "services_metadata"

    def ready(self):
        from .handler import MetadataServicePlugin  # NOQA
