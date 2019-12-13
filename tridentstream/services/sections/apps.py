from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.sections"
    verbose_name = "Sections Service"
    label = "services_sections"

    def ready(self):
        from .handler import SectionsService  # NOQA
