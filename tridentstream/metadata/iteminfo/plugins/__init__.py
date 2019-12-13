import logging

from .plugin import ItemInfoPlugin  # NOQA

logger = logging.getLogger(__name__)


try:
    from .guessit import GuessItItemInfoPlugin  # NOQA
except ImportError:
    logger.warning("Unable to load GuessIt iteminfo, to fix it, please intall guessit")
