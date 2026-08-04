import logging
from config import Settings

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def configure_logging():
    logging.basicConfig(level=Settings.LOG_LEVEL, format=LOG_FORMAT)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


def get_logger(name):
    return logging.getLogger(name)
