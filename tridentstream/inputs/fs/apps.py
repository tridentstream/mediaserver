from django.apps import AppConfig as DjangoAppConfig


class AppConfig(DjangoAppConfig):
    name = "tridentstream.inputs.fs"
    verbose_name = "Filesystem Input"
    label = "inputs_fs"

    def ready(self):
        from .handler import FilesystemInputPlugin  # NOQA
