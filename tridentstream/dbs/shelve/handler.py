import logging
import os
from shelve import DbfilenameShelf

from unplugged import Schema, fields

from ...plugins import DatabasePlugin

logger = logging.getLogger(__name__)


class ShelfDatabaseSchema(Schema):
    path = fields.String()


class ShelfDatabasePlugin(DbfilenameShelf, DatabasePlugin):
    plugin_name = "shelf"

    config_schema = ShelfDatabaseSchema

    _doing_sync = False

    def __init__(self, config):
        self.config = config
        self._open()

    def _open(self):
        DbfilenameShelf.__init__(
            self,
            os.path.join(self.get_database_path(self.config["path"]), "shelfdb.db"),
        )

    def unload(self):
        self.close()

    def __repr__(self):
        return DatabasePlugin.__repr__(self)

    def sync(self):
        if self._doing_sync:
            return

        if self.writeback and self.cache:
            self.writeback = False
            for key, entry in self.cache.items():
                self[key] = entry
            self.writeback = True
            self.cache = {}

        if hasattr(self.dict, "reorganize"):
            # The database might grow too much without an occational reorganize
            # This is not the perfect place to put it but shelve is a bad choice to begin with
            self.dict.reorganize()

        if hasattr(self.dict, "sync"):  # "thanks" python
            self.dict.sync()
        else:
            logger.debug("Doing close/open database sync")
            self._doing_sync = True
            self.close()
            self._open()
            self._doing_sync = False
            logger.debug("Done with close/open database sync")
