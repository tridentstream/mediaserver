import pickle

from unplugged import Schema, fields

import leveldb

from ...plugins import DatabasePlugin


class LevelDBDatabaseSchema(Schema):
    path = fields.String()


class LevelDBDatabasePlugin(DatabasePlugin):
    plugin_name = "leveldb"

    config_schema = LevelDBDatabaseSchema
    loaded = False

    def __init__(self, config):
        self.db = leveldb.LevelDB(self.get_database_path(config["path"]))
        self.loaded = True

    def unload(self):
        self.close()

    def __getitem__(self, key):
        return pickle.loads(self.db.Get(key.encode("utf-8")))

    def __setitem__(self, key, value):
        self.db.Put(key.encode("utf-8"), pickle.dumps(value))

    def __delitem__(self, key):
        self.db.Delete(key.encode("utf-8"))

    def keys(self):
        return list(self.db.RangeIter(include_value=False))

    def __len__(self):
        return len(self.keys())

    def __contains__(self, key):
        try:
            self.db.Get(key.encode("utf-8"))
            return True
        except KeyError:
            return False

    def close(self):
        if self.loaded:
            self.loaded = False
            del self.db

    def sync(self):
        if self.loaded:
            self.db.Put(b"__donotuse", b"", sync=True)
            self.db.Delete(b"__donotuse")

    def __iter__(self):
        if self.loaded:
            return self.db.RangeIter(include_value=False)
        else:
            return []
