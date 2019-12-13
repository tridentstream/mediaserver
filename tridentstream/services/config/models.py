from django.contrib.auth.models import User
from django.db import models
from jsonfield import JSONField


class DefaultSetting(models.Model):
    SYSTEM_DEFAULT = "system"
    CONFIGURED_DEFAULT = "configured"
    DEFAULT_TYPE_CHOICES = (
        (SYSTEM_DEFAULT, "System Default"),
        (CONFIGURED_DEFAULT, "Configured Default"),
    )
    default_type = models.CharField(max_length=30, choices=DEFAULT_TYPE_CHOICES)

    namespace = models.CharField(max_length=100)
    key = models.CharField(max_length=100)
    value = JSONField()

    class Meta:
        unique_together = (("default_type", "namespace", "key"),)


class Setting(models.Model):
    user = models.ForeignKey(User, on_delete=models.deletion.CASCADE)
    namespace = models.CharField(max_length=100)
    key = models.CharField(max_length=100)
    value = JSONField()

    class Meta:
        unique_together = (("user", "namespace", "key"),)
