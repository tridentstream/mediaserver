import logging

logger = logging.getLogger(__name__)


class debugdict(dict):
    synced = False
    closed = False

    def sync(self):
        self.synced = True

    def close(self):
        self.closed = True
