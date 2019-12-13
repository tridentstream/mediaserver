from unplugged import Schema

from ...plugins import DatabasePlugin


class MemoryDatabasePlugin(dict, DatabasePlugin):
    plugin_name = "memory"

    config_schema = Schema

    def __init__(self, config):
        pass

    def unload(self):
        self.clear()

    def sync(self):
        pass

    def close(self):
        pass
