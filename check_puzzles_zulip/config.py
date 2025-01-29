import os

from dotenv import load_dotenv

load_dotenv()


def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = (
            f"Set the {var_name} environment variable, either in .env or via env"
        )
        raise KeyError(error_msg)


ZULIP_CHANNEL = get_env_variable("ZULIP_CHANNEL")
ZULIP_TOPIC = get_env_variable("ZULIP_TOPIC")
ZULIP_REPORTER = get_env_variable("ZULIP_REPORTER")
ZULIPRC = get_env_variable("ZULIPRC")
