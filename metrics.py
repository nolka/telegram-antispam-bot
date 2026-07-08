from prometheus_client import Counter, start_http_server


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
            ],
        )
        self.messages_received_total = Counter(
            "messages_received_total",
            "Total count of received messages from any chats",
            [
                "chat_id",
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
        self.api_errors_total = Counter(
            "api_errors_total",
            "Total number of errors in telegram api",
            [
                "error_class",
            ],
        )
        self.tasks_dropped_total = Counter(
            "tasks_dropped_total",
            "Total number of dropped tasks from queue because of processing errors",
            [],
        )
        self.commands_executed_total = Counter(
            "commands_executed_total",
            "Total number of executed commands",
            [
                "command_name",
                "chat_id",
            ],
        )
        self.spam_message_detected_total = Counter(
            "spam_message_detected_total",
            "Total number of detected spam messages",
            [
                "chat_id",
            ],
        )
        self.spam_message_added_total = Counter(
            "spam_message_added_total",
            "Total number of added spam messages",
            [
                "chat_id",
            ],
        )

    def inc_captha_solved_total(self, captha_code: str):
        self.captha_solved_total.labels(captha_code).inc()

    def inc_members_joined_total(self, chat_id: int):
        self.members_joined_total.labels(chat_id).inc()

    def inc_messages_received_total(self, chat_id: int):
        self.messages_received_total.labels(chat_id).inc()

    def inc_plugin_errors_total(self, plugin_name: str, error_class: str):
        self.plugin_errors_total.labels(plugin_name, error_class).inc()

    def inc_api_errors_total(self, error_class: str):
        self.api_errors_total.labels(error_class).inc()

    def inc_tasks_dropped_total(self):
        self.tasks_dropped_total.inc()

    def inc_commands_executed_total(self, command_name: str, chat_id: int):
        self.commands_executed_total.labels(command_name, chat_id).inc()

    def inc_spam_message_detected_total(self, chat_id: int):
        self.spam_message_detected_total.labels(chat_id).inc()

    def inc_spam_message_added_total(self, chat_id: int):
        self.spam_message_added_total.labels(chat_id).inc()
