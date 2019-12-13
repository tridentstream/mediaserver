from abc import abstractmethod

from unplugged import PluginBase


class HistoryPlugin(PluginBase):
    plugin_type = "history"

    @abstractmethod
    def log_history(self, config, listingitem, viewstate):
        """
        Log a user who watched a listingitem with viewstate, update viewstate if got info.
        """
        raise NotImplementedError
