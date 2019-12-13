from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.player"
    verbose_name = "Player Management Service"
    label = "services_player"

    def ready(self):
        from .handler import PlayerServicePlugin  # NOQA
