from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.searchers.remotesearcher"
    verbose_name = "RemoteSearcher Searcher"
    label = "searchers_remotesearcher"

    def ready(self):
        from .handler import RemoteSearcherSearcher  # NOQA
