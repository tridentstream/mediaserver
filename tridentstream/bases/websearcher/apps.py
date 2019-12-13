from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.bases.websearcher"
    verbose_name = "WebSearcher base"
    label = "searcher_websearcher_base"
