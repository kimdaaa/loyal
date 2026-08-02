import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.getenv("APPDATA"), "rankchecker", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "loyal.log")

_logger = logging.getLogger("loyal")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    _handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    _logger.addHandler(_handler)
    _logger.propagate = False

_TAG_TO_LEVEL = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "action": logging.INFO,
    "success": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def log_to_file(message, tag="info"):
    level = _TAG_TO_LEVEL.get(tag, logging.INFO)
    _logger.log(level, "[%s] %s", tag.upper(), message)


def get_log_path():
    return LOG_PATH
