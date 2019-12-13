from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.bittorrentclients.deluge"
    verbose_name = "Deluge BittorrentClient"
    label = "bittorrentclients_deluge"

    def ready(self):
        from .handler import DelugeBittorrentClientPlugin  # NOQA
