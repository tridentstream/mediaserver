from __future__ import absolute_import

import os
import pkg_resources

import environ

"""
Tridentstream Django settings.
"""

env = environ.Env(
    ALLOWED_HOSTS=(list, ["*"]),
    MEDIA_ROOT=(str, "media"),
    DATABASE_ROOT=(str, "dbs"),
    INSTALLED_APPS=(list, []),
    DISABLE_CSRF_SECURITY=(bool, True),
    PACKAGE_ROOT=(str, ""),
)
env.read_env(env.str("ENV_PATH", ".environ"))

if os.environ.get("DJANGO_DEBUG") == "1":
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {"class": "logging.StreamHandler"},
            "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        },
        "loggers": {
            "django": {"handlers": ["console"], "level": "DEBUG"},
            "django.db.backends": {
                "handlers": ["null"],  # Quiet by default!
                "propagate": False,
                "level": "DEBUG",
            },
            "rebulk.rules": {
                "handlers": ["null"],  # Quiet by default!
                "propagate": False,
                "level": "DEBUG",
            },
        },
    }
    DEBUG = True
else:
    DEBUG = False

# Tridentstream specific apps

DATABASE_APPS = (
    "tridentstream.dbs.leveldb",
    # "tridentstream.dbs.lmdb", # TODO: make auto growing before re-enabling
    "tridentstream.dbs.memory",
    "tridentstream.dbs.shelve",
)

METADATA_APPS = (
    "tridentstream.metadata.imdb",
    "tridentstream.metadata.mal",
    "tridentstream.metadata.embedded",
    "tridentstream.metadata.firstseen",
    "tridentstream.metadata.history",
    "tridentstream.metadata.iteminfo",
    "tridentstream.metadata.thetvdb",
    "tridentstream.metadata.tag",
    "tridentstream.metadata.name",
    "tridentstream.metadata.available",
)

INPUT_APPS = ("tridentstream.inputs.fs", "tridentstream.inputs.rfs")

BASE_APPS = (
    "tridentstream.bases.listing",
    "tridentstream.bases.metadata",
    "tridentstream.bases.websearcher",
)

INDEXER_APPS = ("tridentstream.indexers.whoosh",)

SERVICE_APPS = (
    "tridentstream.services.imgcache",
    "tridentstream.services.metadata",
    "tridentstream.services.config",
    "tridentstream.services.remotesearcher",
    "tridentstream.services.rfs",
    "tridentstream.services.sections",
    "tridentstream.services.store",
    "tridentstream.services.player",
    "tridentstream.services.webinterface",
)

BITTORRENT_CLIENT_APPS = ("tridentstream.bittorrentclients.deluge",)

SEARCHER_APPS = ("tridentstream.searchers.remotesearcher",)

NOTIFIER_APPS = (
    "tridentstream.notifiers.wamp",
    "tridentstream.notifiers.multinotifier",
)

# Application definition

INSTALLED_APPS = (
    (
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "rest_framework",
        "rest_framework.authtoken",
        "rest_framework_filters",
        "corsheaders",
        "channels",
        "unplugged",
        "unplugged.services.admin",
        "unplugged.services.api",
        "unplugged.services.staticurls",
        "unplugged.services.user",
        "unplugged.services.wamp",
        "tridentstream",
    )
    + BASE_APPS
    + DATABASE_APPS
    + INPUT_APPS
    + METADATA_APPS
    + SERVICE_APPS
    + INDEXER_APPS
    + SEARCHER_APPS
    + BITTORRENT_CLIENT_APPS
    + NOTIFIER_APPS
)


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [  # TODO: feedback needed in webinterface
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# DRF settings

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

APPEND_SLASH = False
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = "/djangostatic/"
MEDIA_URL = "/media/"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DEBUG_PROPAGATE_EXCEPTIONS = False

FILESERVE_RESOURCE = None

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

DEBUG_CLEAR_CACHE = False

PLUGIN_INITIALIZATION_ORDER = ["service"]

TRIDENTSTREAM_TEMPLATES = ("cover", "table")

TRIDENTSTREAM_TEMPLATES_NAMES = ("Cover", "Table")

TRIDENTSTREAM_CONTENT_TYPES = (
    "songs",
    "albums",
    "movies",
    "movie",
    "tvshows",
    "seasons",
    "episodes",
)

TRIDENTSTREAM_CONTENT_TYPES_NAMES = (
    "Songs",
    "Albums",
    "Movies",
    "Movie",
    "TV Shows",
    "Seasons",
    "Episodes",
)

ASGI_APPLICATION = "main.routing.application"
SCHEDULER = None

THOMAS_STREAMER_PLUGINS = ["direct", "rar"]

VIDEO_STREAMABLE_EXTENSIONS = ["mkv", "mp4", "iso", "ogg", "ogm", "m4v", "wmv"]
AUDIO_STREAMABLE_EXTENSIONS = ["flac", "mp3", "oga", "m4a"]
STREAMABLE_EXTENSIONS = set(VIDEO_STREAMABLE_EXTENSIONS + AUDIO_STREAMABLE_EXTENSIONS)
WAMP_REALM = "tridentstream"

CACHES = {
    "default": env.cache(default="dbcache://cache_table"),
}

DATABASES = {
    "default": env.db(default="sqlite:///db.sqlite3?timeout=120"),
}

PLUGIN_ENTRY_POINT = "tridentstream.apps"

INSTALLED_APPS += tuple(entry_point.module_name for entry_point in pkg_resources.iter_entry_points(PLUGIN_ENTRY_POINT) if entry_point.name == "app")
INSTALLED_APPS += tuple(env("INSTALLED_APPS"))

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

MEDIA_ROOT = env("MEDIA_ROOT")
DATABASE_ROOT = env("DATABASE_ROOT")
PACKAGE_ROOT = env("PACKAGE_ROOT")

TWISTD_PIDFILE = None

if env("DISABLE_CSRF_SECURITY"):
    MIDDLEWARE += ("main.disablecsrf.DisableCSRFMiddleware",)

for option, option_value in DATABASES["default"].get("OPTIONS", {}).items():
    if option == "timeout":
        DATABASES["default"]["OPTIONS"][option] = int(option_value)
