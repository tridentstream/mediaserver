import logging
import threading
import time
from functools import partial

from django.conf import settings
from unplugged import ServicePlugin, command, threadify
from unplugged.models import Schedule

from .listingbuilder import ListingBuilder
from .models import ListingItem

logger = logging.getLogger(__name__)


class BaseListingService(ServicePlugin):
    _do_unload = False
    can_automatically_rebuild = True
    automatic_rebuild_timer = 15

    def __init__(self, config):
        self.config = config
        self.listing_builder = ListingBuilder(self)
        self.automatic_rebuild_lock = threading.Lock()

        if self.can_automatically_rebuild:
            # TODO: should run after bootstrap
            threadify(self.schedule_automatic_rebuild, delay=3)()
            threadify(self.rebuild_listings, delay=30)()

    def get_section(self, section_name):
        for section in self.config.get("sections", []):
            if section["name"] == section_name:
                return section.copy()

    @command(
        name="clear",
        display_name="Clear",
        description="Clear all cached listings and rebuild them on access",
    )
    def command_clear(self):
        logger.info("Clearing cached listings")
        ListingItem.objects.filter(app=self.name).delete()

    def schedule_automatic_rebuild(self):
        Schedule.objects.ensure_schedule(
            Schedule.METHOD_INTERVAL,
            f"minutes={self.automatic_rebuild_timer}",
            "rebuild_listings",
            {},
            self,
            "automatic_rebuild_listing",
        )

    @command(
        name="rebuild_listings",
        display_name="Rebuild listings",
        description="Try to rebuild all the listings that allows for automatic rebuild",
    )
    def rebuild_listings(self):
        logger.debug(f"We got call for automatic rebuild for {self.name}")
        if settings.DEBUG_CLEAR_CACHE:
            logger.debug("Skipping automatic rebuild due to clear cache debug option")
            return

        if self.automatic_rebuild_lock.locked():
            logger.debug("Automatic rebuild already in progress, bailing")
            return

        with self.automatic_rebuild_lock:
            for section in self.config.get("sections", []):
                logger.debug(
                    f"Checking if we can rebuild service:{self.name} section:{section['name']}"
                )
                if self._do_unload:
                    logger.debug(
                        f"Not rebuilding because we are unloading service:{self.name} section:{section['name']}"
                    )
                    return

                if not section.get("rebuild_automatically"):
                    logger.debug(
                        f"This one does not automatically rebuild at all service:{self.name} section:{section['name']}"
                    )
                    continue

                config = self.get_path_config(section["name"])
                if not config:
                    logger.debug(
                        f"No config found service:{self.name} section:{section['name']}"
                    )
                    continue

                logger.debug(
                    f"Automatic rebuild for service:{self.name} section:{section['name']}"
                )
                self.rebuild_listing(config, section["name"])

    # TODO:
    # if queued, do not build
    # if queued the last 10 seconds, do not build
    def rebuild_listing(self, config, path, delay=False):
        threadify(self.listing_builder.get_listing, delay=delay and 3.0 or 0)(
            config, path, use_background_recheck=False
        )

    def unload(self):
        self._do_unload = True

        super().unload()

    def get_path_config(self, path):
        """
        Returns config for a given path, if None is returned then the lister will try to see
        if the listingitem already exists.
        """
        path = path.split("/")
        section = path.pop(0)
        depth = len(path)
        path = "/".join(path)

        logger.debug(f"Looking for path:{path} in section:{section} with depth:{depth}")

        config = self.get_section(section)
        if not config:
            logger.info("Section config returned None")
            return None

        max_depth = 0
        for level_config in config["levels"]:
            max_depth = max(max_depth, level_config["depth"])
            if level_config["depth"] == depth:
                config["level"] = level_config.copy()

        config["parent_level_config"] = None
        config["path"] = path
        config["section"] = section
        config["edge_type"] = (
            config.get("level", {}).get("depth", -1) == max_depth and "file" or "folder"
        )

        config["levels"] = sorted(config["levels"], key=lambda x: x["depth"])
        for i, level_config in enumerate(config["levels"]):
            if level_config["depth"] == depth:
                config["current_level"] = i
                break
            else:
                config["parent_level_config"] = level_config

        return config

    def get_nearest_config(self, path):
        """
        Finds the nearest parent config and returns it including parent_path
        """
        config = None
        parent_path = path
        while parent_path and (not config or config.get("level") is None):
            parent_path = parent_path.rsplit("/", 1)[0]
            config = self.get_path_config(parent_path)

            if "/" not in parent_path:
                break

        return config, parent_path
