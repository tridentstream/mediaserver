import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_save
from unplugged.models import Log

logger = logging.getLogger(__name__)


def log_user_logged_in(sender, request, user, **kwargs):
    with Log.objects.start_chain(None, "USER.LOGIN_SUCCESS", user) as log:
        log.log(100, f"Logged in from IP {request.META.get('REMOTE_ADDR')}")


def log_user_logged_out(sender, request, user, **kwargs):
    if not user:
        return

    with Log.objects.start_chain(None, "USER.LOGOUT", user) as log:
        log.log(100, f"Logged out from IP {request.META.get('REMOTE_ADDR')}")


def log_user_login_failed(sender, credentials, request, **kwargs):
    try:
        user = User.objects.get(username=credentials.get("username", None))
    except User.DoesNotExist:
        logger.debug(
            "Unknown user %s tried to login" % (credentials.get("username", None),)
        )
        return

    with Log.objects.start_chain(None, "USER.LOGIN_FAILED", user) as log:
        log.log(100, f"Failed to login from IP {request.META.get('REMOTE_ADDR')}")


def log_user_created(sender, instance, created, **kwargs):
    if created:
        with Log.objects.start_chain(None, "USER.CREATED", instance) as log:
            log.log(100, f"Created")


def register_signals():
    user_logged_in.connect(log_user_logged_in, dispatch_uid="log_user_logged_in")
    user_logged_out.connect(log_user_logged_out, dispatch_uid="log_user_logged_out")
    user_login_failed.connect(
        log_user_login_failed, dispatch_uid="log_user_login_failed"
    )
    post_save.connect(log_user_created, sender=User, dispatch_uid="log_user_created")
