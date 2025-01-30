import logging
import os

from dotenv import load_dotenv

import logging
import logging.handlers
import sys

#############
# Constants #
#############

LOG_PATH = f"{__package__}.log"


########
# Logs #
########


def setup_logger(name: str):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    format_string = "%(asctime)s | %(levelname)-8s | %(message)s"

    # 125000000 bytes = 12.5Mb
    handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=12500000, backupCount=3, encoding="utf8"
    )
    handler.setFormatter(logging.Formatter(format_string))
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)

    handler_2 = logging.StreamHandler(sys.stdout)
    handler_2.setFormatter(logging.Formatter(format_string))
    handler_2.setLevel(logging.INFO)
    if __debug__:
        handler_2.setLevel(logging.DEBUG)
    log.addHandler(handler_2)
    return log


log = setup_logger(__file__)

##########
# Config #
##########

load_dotenv()


def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = (
            f"Set the {var_name} environment variable, either in .env or via env"
        )
        raise KeyError(error_msg)


STOCKFISH = get_env_variable("STOCKFISH")
log.debug(f"STOCKFISH: {STOCKFISH}")

ZULIP_CHANNEL = get_env_variable("ZULIP_CHANNEL")
ZULIP_TOPIC = get_env_variable("ZULIP_TOPIC")
ZULIP_REPORTER = get_env_variable("ZULIP_REPORTER")
ZULIPRC = get_env_variable("ZULIPRC")
