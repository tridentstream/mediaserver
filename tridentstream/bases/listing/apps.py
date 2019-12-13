from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.bases.listing"
    verbose_name = "Listing base"
    label = "services_listing"
