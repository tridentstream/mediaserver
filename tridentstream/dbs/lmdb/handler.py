import pickle

from unplugged import Schema, fields

import lmdb

from ...plugins import DatabasePlugin


class LMDBDatabaseSchema(Schema):
    path = fields.String()


class LMDBDatabasePlugin(DatabasePlugin):
    plugin_name = "lmdb"

    config_schema = LMDBDatabaseSchema

    def __init__(self, config):
        self.db = lmdb.open(
            self.get_database_path(config["path"]),
            map_size=500 * 1024 * 1024,  # TODO: autoscale
            map_async=True,
            writemap=True,
            metasync=False,
        )

    def unload(self):
        self.close()

    def __getitem__(self, key):
        with self.db.begin() as txn:
            value = txn.get(key.encode("utf-8"))
            if value:
                return pickle.loads(value)

    def __setitem__(self, key, value):
        with self.db.begin(write=True) as txn:
            txn.put(key.encode("utf-8"), pickle.dumps(value))

    def __delitem__(self, key):
        with self.db.begin(write=True) as txn:
            txn.delete(key.encode("utf-8"))

    def keys(self):
        return [k for k, v in self.db.cursor()]

    def __len__(self):
        return int(self.db.stat()["entries"])

    def __contains__(self, key):
        return self[key] is not None

    def close(self):
        self.db.close()

    def sync(self):
        self.db.sync()

    def __iter__(self):
        return self.db.cursor()
