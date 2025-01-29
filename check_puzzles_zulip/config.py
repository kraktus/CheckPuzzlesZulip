import os

from dotenv import load_dotenv

load_dotenv()


ZULIP_CHANNEL = os.getenv("ZULIP_CHANNEL")
ZULIP_TOPIC = os.getenv("ZULIP_TOPIC")
ZULIPRC = os.getenv("ZULIPRC")