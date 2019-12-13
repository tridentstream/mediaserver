from abc import abstractmethod

from unplugged import PluginBase


class ConfigPlugin(PluginBase):
    plugin_type = "config"
    default_types = ["configured", "system"]

    @abstractmethod
    def get_default_config(self, namespace, key):
        """
        Returns the default configuration for a given key in a
        namespace, if it exists
        """
        raise NotImplementedError

    @abstractmethod
    def get_user_config(self, user, namespace, key):
        """
        Returns the user configuration for a given key in a given namespace
        if it exists, otherwise it returns default config.
        """
        raise NotImplementedError

    @abstractmethod
    def set_default_config(self, default_type, namespace, key, value):
        """
        Sets a default config for a given key in a namespace to value.
        """
        raise NotImplementedError

    @abstractmethod
    def set_user_config(self, user, namespace, key, value):
        """
        Sets a user config for a given key in a namespace to value.
        """
        raise NotImplementedError

    @abstractmethod
    def set_config_schema(self, namespace, key, schema):
        """
        Set a marshmallow schema usable for this specific namespace/key.

        Should not be persistent
        """
        raise NotImplementedError

    @abstractmethod
    def get_config_schema(self, namespace, key):
        """
        Get a marshmallow schema usable for this specific namespace/key if available.

        """
        raise NotImplementedError
