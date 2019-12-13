from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.inputs.rfs"
    verbose_name = "RemoteFilesystem Input"
    label = "inputs_rfs"

    def ready(self):
        from .handler import RemoteFilesystemInputPlugin  # NOQA
