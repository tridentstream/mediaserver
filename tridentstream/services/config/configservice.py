from unplugged import Schema

from ...plugins import ConfigPlugin
from .models import DefaultSetting, Setting


class ConfigConfigPlugin(ConfigPlugin):
    plugin_name = "config"
    config_schema = Schema

    def __init__(self, config):
        super(ConfigConfigPlugin, self).__init__(config)

        self.schemas = {}

    def get_default_config(self, namespace, key):
        for default_type in self.default_types:
            try:
                return DefaultSetting.objects.get(
                    default_type=default_type, namespace=namespace, key=key
                ).value
            except DefaultSetting.DoesNotExist:
                pass
        return None

    def get_user_config(self, user, namespace, key):
        try:
            return Setting.objects.get(user=user, namespace=namespace, key=key).value
        except Setting.DoesNotExist:
            return self.get_default_config(namespace, key)

    def set_default_config(self, default_type, namespace, key, value):
        try:
            s = DefaultSetting.objects.get(
                default_type=default_type, namespace=namespace, key=key
            )
        except DefaultSetting.DoesNotExist:
            s = DefaultSetting(default_type=default_type, namespace=namespace, key=key)

        if value is None:
            s.delete()
        else:
            s.value = value
            s.save()

    def set_user_config(self, user, namespace, key, value):
        try:
            s = Setting.objects.get(user=user, namespace=namespace, key=key)
        except Setting.DoesNotExist:
            s = Setting(user=user, namespace=namespace, key=key)

        if value is None:
            s.delete()
        else:
            s.value = value
            s.save()

    def set_config_schema(self, namespace, key, schema):
        self.schemas[(namespace, key)] = schema

    def get_config_schema(self, namespace, key):
        return self.schemas.get((namespace, key))
