import zulip

# Pass the path to your zuliprc file here.
client = zulip.Client(config_file="~/zuliprc")


SEARCH_PARAMETERS: dict[str, Any] = {
    "anchor": "oldest",
    "narrow": [
        {"operator": "channel", "operand": "Verona"},
        {"operator": "topic", "operand": "iago@zulip.com"},

    ],
}

class ZulipClient(zulip.Client):

    def get_reports(self):
        return self.get_messages(SEARCH_PARAMETERS).messages

    def send_message(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.send_message(request)


# Get the 100 last messages sent by "iago@zulip.com" to
# the channel named "Verona".

result = client.get_messages(request)
print(result)