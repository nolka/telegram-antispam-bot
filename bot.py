from queue import Queue
from random import choice, seed, shuffle
from threading import Thread

import telebot

import views
from logger import Logger
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
        self, method_name: str, kwargs: dict, tries: int = 1, max_tries: int = 3
    ) -> None:
        self.method_name = method_name
        self.kwargs = kwargs
        self.tries = tries
        self.max_tries = max_tries


class Engine:
    """
    Represents wrapper for telebot for implement custom logic for event processing
    """
    emojies = ["❤️", "🙈", "💋", "😭", "😡", "😚"]

    def __init__(
        self,
        bot_username: str,
        bot: telebot.TeleBot,
        storage: AbstractStorage,
        logger: Logger,
    ) -> None:
        self.bot_username = bot_username
        self._bot = bot
        self._storage = storage
        self._logger = logger

        self._member_plugins = []
        self._msg_queue = Queue()
        self._reply_queue = Queue(25)

        self._threads = [
            Thread(target=self._send_message_queue, args=(self._reply_queue,)),
        ]

        self._bot.register_message_handler(
            self._chat_member_joins, content_types=["new_chat_members"]
        )
        self._bot.register_message_handler(self._chat_message, content_types=["text"])
        self._bot.register_callback_query_handler(self._user_selected_answer, func=None)

    def start(self) -> None:
        """
        Starts bot engine
        """
        for thread in self._threads:
            thread.start()
        self.log("Start polling...")
        self._bot.infinity_polling(skip_pending=True)

    def stop(self) -> None:
        """
        Stops bot engine
        """
        for _ in range(len(self._threads)):
            self._reply_queue.put(QueueExit)

        for thread in self._threads:
            thread.join()

        self._bot.stop_bot()
        self.log("Bot stopped")

    def is_user_confirmed(self, group_id, user_id: int) -> bool:
        """Performs check, if user already passed antispam validation"""
        return self._storage.is_user_confirmed(group_id, user_id)

    def add_plugin(self, plugin) -> None:
        """Add user plugin to bot engine"""
        self._member_plugins.append(plugin)

    def send_message(self, **kwargs) -> None:
        """
        Send message through queue to telegram
        """
        self._reply_queue.put(EngineTask("send_message", kwargs))

    def delete_message(self, chat_id, message_id: int) -> None:
        """
        Delete existing message in group via queue
        """
        self._reply_queue.put(
            EngineTask("delete_message", {"chat_id": chat_id, "message_id": message_id})
        )

    def kick_chat_member(self, chat_id: int, user_id: int):
        """Remove chat member from group without ban"""
        self._reply_queue.put(
            EngineTask("kick_chat_member", {"chat_id": chat_id, "user_id": user_id})
        )

    def ban_user(self, chat_id: int, user_id: int) -> None:
        """Permanently ban user from group"""
        self._reply_queue.put(
            EngineTask("ban_chat_member", {"chat_id": chat_id, "user_id": user_id})
        )

    def _send_message_queue(self, queue: Queue):
        while True:
            task = queue.get()
            try:
                if task == QueueExit:
                    return

                exec_method = getattr(self._bot, task.method_name)
                self.log(f"Execing method '{task.method_name}'")
                exec_method(**task.kwargs)
            except Exception as e:
                self.log(e, "error")
                if task.tries <= task.max_tries:
                    task.tries += 1
                    queue.put(task)
                else:
                    self.log("Task dropped because max retry limit exceeded")
            finally:
                queue.task_done()

    def log(self, msg: str, severity: str = "info", module_name: str = "") -> None:
        if severity == "error":
            self._logger.error(msg, module_name)
            return

        self._logger.info(msg, module_name)

    def _chat_member_joins(self, message: telebot.types.Message):
        # Hotfix for handling messages from groups when storage does not have
        # info about where bot is member. TODO Make pretty solution
        self._storage.on_added_to_group(message.chat.id)

        if self._run_member_plugins(message):
            return

        for new_member in message.new_chat_members:
            if new_member.username == self.bot_username:
                self._bot_added_to_group(message.chat.id)
                continue

            if self._storage.is_user_confirmed(message.chat.id, new_member.id):
                continue

            confirm_code = self._storage.get_user_confirm_code(
                message.chat.id, new_member.id
            )
            if confirm_code is None or not confirm_code:
                seed()
                confirm_code = choice(self.emojies)
                self._storage.set_user_confirm_code(
                    message.chat.id, new_member.id, confirm_code
                )

            self.send_message(
                chat_id=message.chat.id,
                text=views.render_new_member_joined_message(
                    {
                        "new_member": new_member,
                        "confirm_code": confirm_code,
                    }
                ),
                parse_mode="markdownV2",
                reply_markup=self._get_emoji_keyboard(),
            )

    def _run_member_plugins(self, message: telebot.types.Message) -> bool:
        for plugin in self._member_plugins:
            try:
                if plugin.execute(self, message):
                    return True
            except Exception as e:
                cls_name = plugin.__class__.__name__
                self.log(
                    f"Unhandled error in plugin {cls_name}:\n{e}",
                    "error",
                )
        return False

    def _get_emoji_keyboard(self) -> telebot.types.InlineKeyboardMarkup:
        shuffle(self.emojies)
        return telebot.types.InlineKeyboardMarkup(
            [
                [
                    telebot.types.InlineKeyboardButton(x, callback_data=x)
                    for x in self.emojies
                ]
            ]
        )

    def _bot_added_to_group(self, group_id: int):
        self._storage.on_added_to_group(group_id)

    def _chat_message(self, message):
        # Hotfix for handling messages from groups when storage does not have
        # info about where bot is member. TODO Make pretty solution
        self._storage.on_added_to_group(message.chat.id)

        if not self._storage.is_user_confirmed(
            message.chat.id, message.from_user.id
        ) and not self._storage.get_user_confirm_code(
            message.chat.id, message.from_user.id
        ):
            # user added in group before bot
            return
        if not self._storage.is_user_confirmed(message.chat.id, message.from_user.id):
            self.delete_message(chat_id=message.chat.id, message_id=message.id)

    def _user_selected_answer(self, callback: telebot.types.CallbackQuery):
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id

        if (
            not self._storage.is_user_confirmed(chat_id, user_id)
            and self._storage.get_user_confirm_code(chat_id, user_id) == callback.data
        ):
            self._storage.set_user_confirmed(chat_id, user_id)
            self.delete_message(chat_id=chat_id, message_id=callback.message.id)
