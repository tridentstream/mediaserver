from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.webinterface"
    verbose_name = "Webinterface Service"
    label = "services_webinterface"

    def ready(self):
        from .handler import WebinterfaceServicePlugin  # NOQA
