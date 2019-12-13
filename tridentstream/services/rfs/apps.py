from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.rfs"
    verbose_name = "RemoteFileSystem Service"
    label = "services_rfs"

    def ready(self):
        from .handler import RemoteFilesystemService  # NOQA
