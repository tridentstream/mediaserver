from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.bases.metadata"
    verbose_name = "Metadata base"
    label = "metadata_base"
