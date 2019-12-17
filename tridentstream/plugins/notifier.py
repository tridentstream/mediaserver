import fnmatch
import logging
from abc import abstractmethod

from unplugged import PluginBase, Schema, fields

logger = logging.getLogger(__name__)


class Notification:
    def __init__(
        self,
        topic,
        notification_type,
        title,
        body,
        permission_type=None,
        permission_config=None,
    ):
        self.topic = topic

        self.type = notification_type
        self.title = title
        self.body = body

        self.permission_type = permission_type
        self.permission_config = permission_config

    def is_allowed(self, user):
        if self.permission_type == "user":
            return user.username in self.permission_config.get("usernames", [])
        elif self.permission_type == "permission":
            return user.has_perm(self.permission_config.get("permission"))
        elif self.permission_type == "is_admin":
            return user.is_superuser
        elif self.permission_type == None:
            return True
        else:
            logger.warning(f"Unknown permission_type: {self.permission_type}")
            return False

    def match_patterns(self, patterns):
        return any(fnmatch.fnmatch(self.topic, pattern) for pattern in patterns)

    def copy(
        self,
        topic=None,
        notification_type=None,
        title=None,
        body=None,
        permission_type=None,
        permission_config=None,
    ):
        if topic is None:
            topic = self.topic

        if notification_type is None:
            notification_type = self.type

        if title is None:
            title = self.title

        if body is None:
            body = self.body

        if permission_type is None:
            permission_type = self.permission_type

        if permission_config is None:
            permission_config = self.permission_config

        return self.__class__(
            topic, notification_type, title, body, permission_type, permission_config
        )


class NotifierPlugin(PluginBase):
    plugin_type = "notifier"

    @abstractmethod
    def notify(self, notification):
        """
        Send a notification to whoever is concerned.
        """
        raise NotImplementedError
