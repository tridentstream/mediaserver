from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.notifiers.wamp"
    verbose_name = "WAMP Notifier"
    label = "notifier_wamp"

    def ready(self):
        from .handler import WAMPNotifierHandlerPlugin  # NOQA
