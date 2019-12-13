from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.notifiers.multinotifier"
    verbose_name = "MultiNotifier Notifier"
    label = "notifier_multinotifier"

    def ready(self):
        from .handler import MultiNotifierNotifierHandlerPlugin  # NOQA
