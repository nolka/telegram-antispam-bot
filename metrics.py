from prometheus_client import start_http_server, Counter


def start_metrics_server(port: int, host: str = "0.0.0.0"):
    start_http_server(port, host)


class BotMetrics:
    def __init__(self) -> None:
        self.captha_solved_total = Counter(
            "captha_solved_total",
            "Total capthas solved",
            [
                "captha_code",
            ],
        )
        self.members_joined_total = Counter(
            "members_joined_total",
            "Total count of joined members",
            [
                "chat_id",
                "user_id",
            ],
        )
        self.messages_received_total = Counter(
            "messages_received_total",
            "Total count of received messages from any chats",
            [
                "chat_id",
                "user_id",
            ],
        )
        self.plugin_errors_total = Counter(
            "plugin_errors_total",
            "Total number of errors in pluging",
            [
                "plugin_name",
                "error_class",
            ],
        )
        self.commands_executed_total = Counter(
            "commands_executed_total",
            "Total number of executed commands",
            [
                "command_name",
                "chat_id",
            ],
        )

    def inc_captha_solved_total(self, captha_code: str):
        self.captha_solved_total.labels(captha_code).inc()

    def inc_members_joined_total(self, chat_id: int, user_id: int):
        self.members_joined_total.labels(chat_id, user_id).inc()

    def inc_messages_received_total(self, chat_id: int, user_id: int):
        self.messages_received_total.labels(chat_id, user_id).inc()

    def inc_plugin_errors_total(self, plugin_name: str, error_class: str):
        self.plugin_errors_total.labels(plugin_name, error_class).inc()

    def inc_commands_executed_total(self, command_name: str, chat_id: int):
        self.commands_executed_total.labels(command_name, chat_id).inc()
