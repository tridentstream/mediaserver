from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.remotesearcher"
    verbose_name = "RemoteSearcher Service"
    label = "services_remotesearcher"

    def ready(self):
        from .handler import RemoteSearcherService  # NOQA
