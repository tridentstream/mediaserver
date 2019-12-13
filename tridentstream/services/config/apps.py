from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.config"
    verbose_name = "Config Service"
    label = "services_config"

    def ready(self):
        from .handler import ConfigServicePlugin  # NOQA
        from .configservice import ConfigConfigPlugin  # NOQA
