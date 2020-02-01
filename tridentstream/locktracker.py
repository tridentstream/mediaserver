import logging
from datetime import timedelta
from threading import Event, Lock

from django.utils.timezone import now

logger = logging.getLogger(__name__)


class PathLockTracker:
    def __init__(self, locktracker, path):
        self.path = path
        self.locktracker = locktracker
        self.waited = False
        self.expired = False

    def __enter__(self):
        logger.debug(f"Trying to figure out how to handle the lock of path:{self.path}")

        found_existing_lock = False
        with self.locktracker.build_lock:
            if self.path in self.locktracker.locks:
                logger.debug("Existing lock found, lets check if it is timed out yet")
                event, started = self.locktracker.locks[self.path]
                end_time = started + self.locktracker.wait_time
                if end_time < now():
                    logger.info("Found lock that is timed out.")
                else:
                    found_existing_lock = True

            if not found_existing_lock:
                logger.debug("No locks found, lets create one")
                self.locktracker.locks[self.path] = Event(), now()

        if found_existing_lock:
            logger.debug("Found working existing lock, waiting for that.")
            self.waited = True
            wait_time = (now() - end_time) + timedelta(seconds=1)
            if not event.wait(wait_time.total_seconds()):
                self.expired = True

        return self

    def __exit__(self, type_, value, traceback):
        logger.debug(f"Done with one event of path:{self.path}")
        if not self.waited:
            with self.locktracker.build_lock:
                if self.path in self.locktracker.locks:
                    del self.locktracker.locks[self.path]
                else:
                    logger.warning(f"Was unable to delete event for path:{self.path}")


class LockTracker:
    wait_time = timedelta(minutes=5)

    def __init__(self):
        self.build_lock = Lock()
        self.locks = {}

    def get_path(self, path):
        logger.debug(f"Handling lock for path:{path}")
        return PathLockTracker(self, path)
