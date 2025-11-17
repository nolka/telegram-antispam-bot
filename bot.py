import traceback
from collections import defaultdict
from queue import Queue
from threading import Thread

import telebot
from telebot.apihelper import ApiException
from telebot.types import ReactionTypeEmoji

import plugins
from entities.delayed_response import DelayedResponseQueue
from logger import Logger
from metrics import BotMetrics
from storage import AbstractStorage


class QueueExit:
    """
    Class used to exid from worker threads
    """


class EngineTask:
    """
    Class used to execute telegram bot api methods through worker thread using queue
    """

    def __init__(
        self,
        method_name: str,
        kwargs: dict,
        tries: int = 1,
        max_tries: int = 3,
        response_queue: DelayedResponseQueue = None,
    ) -> None:
        self.method_name: str = method_name
        self.kwargs: dict = kwargs
        self.tries: int = tries
        self.max_tries: int = max_tries
        self.response_queue: DelayedResponseQueue = response_queue


class Engine:
    """
    Represents wrapper for telebot for implement custom logic for event processing
    """

    def __init__(
        self,
        bot_username: str,
        bot: telebot.TeleBot,
        metrics: BotMetrics,
        storage: AbstractStorage,
        logger: Logger,
    ) -> None:
        self.bot_username = bot_username
        self._bot = bot
        self._metrics = metrics
        self._storage = storage
        self._logger = logger

        self._plugins: dict = defaultdict(list)
        self._msg_queue = Queue()
        self._reply_queue = Queue(25)
        self._admins: list[int] = list()

        self._threads = [
            Thread(target=self._send_message_queue, args=(self._reply_queue,)),
        ]

        self._bot.register_message_handler(
            self._chat_member_joins, content_types=["new_chat_members"]
        )
        self._bot.register_message_reaction_handler(self._chat_member_reactions)
        self._bot.register_message_handler(self.on_chat_message, content_types=["text"])

    def start(self) -> None:
        """
        Starts bot engine
        """
        for thread in self._threads:
            thread.start()
        self.log("Start polling...")
        self._bot.infinity_polling()

    def stop(self) -> None:
        """
        Stops bot engine
        """
        for _ in range(len(self._threads)):
            self._reply_queue.put(QueueExit)

        # terminating threads
        for thread in self._threads:
            thread.join()

        # greceful terminating plugins
        for plugin_type in self._plugins.keys():
            while len(self._plugins[plugin_type]):
                plugin = self._plugins[plugin_type].pop()
                exitfunc = getattr(plugin, "exit", None)
                if exitfunc:
                    exitfunc()

        self._bot.stop_bot()
        self.log("Bot stopped")

    def add_admins(self, admins: list[int] | str) -> None:
        """Set bot admins"""
        if not admins:
            return

        if isinstance(admins, str):
            self._admins = [int(x) for x in admins.split(",")]
        if isinstance(admins, list):
            self._admins = [int(x) for x in admins]

    def is_user_admin(self, user_id: int) -> bool:
        return user_id in self._admins

    @property
    def storage(self) -> AbstractStorage:
        """Storage getter"""
        return self._storage

    @property
    def metrics(self) -> BotMetrics:
        """Metrics getter"""
        return self._metrics

    def add_callback_query_handler(self, callback: callable, **kwargs) -> None:
        self._bot.register_callback_query_handler(callback, **kwargs)

    def add_plugin(self, plugin) -> None:
        """Add user plugin to bot engine"""

        self._plugins[plugin.plugin_type].append(plugin)

        self.log(f"Registered plugin: {plugin.__class__.__name__}")

    def send_message(self, reply_to: DelayedResponseQueue = None, **kwargs) -> Queue:
        """
        Send message through queue to telegram
        """
        task = EngineTask("send_message", kwargs, response_queue=reply_to)
        self._reply_queue.put(task)
        return task.response_queue

    def delete_message(self, chat_id, message_id: int) -> None:
        """
        Delete existing message in group via queue
        """
        self._reply_queue.put(
            EngineTask("delete_message", {"chat_id": chat_id, "message_id": message_id})
        )

    def set_message_reaction(self, chat_id, message_id: int, reaction: str) -> None:
        self._reply_queue.put(
            EngineTask(
                "set_message_reaction",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reaction": (ReactionTypeEmoji(reaction),),
                },
            )
        )

    def kick_chat_member(self, chat_id: int, user_id: int):
        """DEPRECATED. Remove chat member from group without ban"""
        self._reply_queue.put(
            EngineTask("kick_chat_member", {"chat_id": chat_id, "user_id": user_id})
        )

    def ban_chat_member(self, chat_id: int, user_id: int, revoke_messages: bool):
        """Ban member from chat"""
        self._reply_queue.put(
            EngineTask(
                "ban_chat_member",
                {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "revoke_messages": revoke_messages,
                },
            )
        )

    def ban_user(self, chat_id: int, user_id: int) -> None:
        """Permanently ban user from group"""
        self._reply_queue.put(
            EngineTask("ban_chat_member", {"chat_id": chat_id, "user_id": user_id})
        )

    def _send_message_queue(self, queue: Queue):
        while True:
            task: EngineTask = queue.get()
            try:
                if task == QueueExit:
                    return

                exec_method = getattr(self._bot, task.method_name)
                self.log(f"Execing method '{task.method_name}'")
                response = exec_method(**task.kwargs)
                if task.response_queue:
                    task.response_queue.put(response)

                self._metrics.inc_commands_executed_total(
                    task.method_name, task.kwargs.get("chat_id", 0)
                )
            except ApiException as exc:
                self.metrics.inc_api_errors_total(exc.__class__.__name__)
                self.log(
                    f"Unhandled ApiException: {exc.function_name} -> {exc.result}:\n{exc}\n{traceback.format_exc()}",
                    severity="error",
                )

            except Exception as exc:
                self.metrics.inc_api_errors_total(exc.__class__.__name__)
                self.log(
                    f"Unhandled Exception: {exc}\n{traceback.format_exc()}",
                    "error",
                )
                if task.tries <= task.max_tries:
                    task.tries += 1
                    queue.put(task)
                else:
                    self.log("Task dropped because max retry limit exceeded")

            finally:
                queue.task_done()

    def log(self, msg: str, severity: str = "info") -> None:
        """Writes log message"""
        match severity:
            case "error":
                self._logger.error(msg)
            case _:
                self._logger.info(msg)

    def _chat_member_joins(self, message: telebot.types.Message):
        # Hotfix for handling messages from groups when storage does not have
        # info about where bot is member. TODO Make pretty solution
        self._storage.on_added_to_group(message.chat.id)

        self._metrics.inc_members_joined_total(message.chat.id, message.from_user.id)

        if self._run_plugins(plugins.PLUGIN_NEW_CHAT_MEMBER, message):
            return

    def _chat_member_reactions(self, message: telebot.types.Message):
        # self.log(f"got reaction: {message}")
        # self._storage.on_added_to_group(message.chat.id)

        # self._metrics.inc_members_joined_total(message.chat.id, message.from_user.id)

        if self._run_plugins(plugins.PLUGIN_NEW_CHAT_MESSAGE, message):
            return

    def _run_plugins(
        self,
        plugin_type: int,
        message: telebot.types.Message | telebot.types.MessageReactionUpdated,
    ) -> bool:
        for plugin in self._plugins[plugin_type]:
            try:
                match message.__class__:
                    case telebot.types.Message:
                        handler_name = "execute"
                    case telebot.types.MessageReactionUpdated:
                        handler_name = "execute_reaction"

                handler = getattr(plugin, handler_name, None)
                if not handler:
                    self.log(
                        f"Plugin {plugin.__class__.__name__} does not have method {handler_name}",
                        "warning",
                    )
                    continue

                if handler(self, message):
                    return True
            except Exception as exc:
                cls_name = plugin.__class__.__name__
                self.log(
                    f"Unhandled error in plugin {cls_name}:\n{exc}\n{traceback.format_exc()}",
                    "error",
                )
                self._metrics.inc_plugin_errors_total(cls_name, exc.__class__.__name__)
        return False

    def on_bot_added_to_group(self, group_id: int):
        """Fired when bot added to new group"""
        self._storage.on_added_to_group(group_id)

    def on_chat_message(self, message):
        # Hotfix for handling messages from groups when storage does not have
        # info about where bot is member. TODO Make pretty solution
        self._storage.on_added_to_group(message.chat.id)

        self._metrics.inc_messages_received_total(message.chat.id, message.from_user.id)

        if self._run_plugins(plugins.PLUGIN_NEW_CHAT_MESSAGE, message):
            return

        if not self.storage.is_user_confirmed(
            message.chat.id, message.from_user.id
        ) and not self.storage.get_user_confirm_code(message.chat.id, message.from_user.id):
            # user added in group before bot
            return
        if not self.storage.is_user_confirmed(message.chat.id, message.from_user.id):
            self.delete_message(chat_id=message.chat.id, message_id=message.id)
