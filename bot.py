import telebot
from queue import Queue
from threading import Thread, Timer
from random import choice, shuffle, seed
import views

from storage import AbstractStorage


class _Task:
    def __init__(
        self, method_name: str, kwargs: dict, tries: int = 1, max_tries: int = 3
    ) -> None:
        self.method_name = method_name
        self.kwargs = kwargs
        self.tries = tries
        self.max_tries = max_tries


class Engine:
    emojies = ["❤️", "🙈", "💋", "😭", "😡", "😚"]

    def __init__(
        self, bot_username: str, bot: telebot.TeleBot, storage: AbstractStorage
    ) -> None:
        self.bot_username = bot_username
        self._bot = bot
        self._storage = storage

        self._member_plugins = []
        self._msg_queue = Queue()
        self._reply_queue = Queue(25)

        self._threads = [
            Thread(target=self._handle_message_queue, args=(self._msg_queue,)),
            Thread(target=self._send_message_queue, args=(self._reply_queue,)),
        ]

        self._bot.register_message_handler(
            self._chat_member_joins, content_types=["new_chat_members"]
        )
        self._bot.register_message_handler(self._chat_message, content_types=["text"])
        self._bot.register_callback_query_handler(self._user_selected_answer, func=None)

    def start(self) -> None:
        for t in self._threads:
            t.start()

        self._bot.infinity_polling(skip_pending=True)

    def stop(self) -> None:
        for t in self._threads:
            t.join()

        self._bot.stop_bot()

    def is_user_confirmed(self, group_id, user_id: int) -> bool:
        return self._storage.is_user_confirmed(group_id, user_id)

    def add_plugin(self, plugin) -> None:
        self._member_plugins.append(plugin)

    def send_message(self, **kwargs) -> None:
        self._reply_queue.put(_Task("send_message", kwargs))

    def delete_message(self, chat_id, message_id: int) -> None:
        self._reply_queue.put(
            _Task("delete_message", {"chat_id": chat_id, "message_id": message_id})
        )

    def kick_chat_member(self, chat_id: int, user_id: int):
        self._reply_queue.put(
            _Task("kick_chat_member", {"chat_id": chat_id, "user_id": user_id})
        )

    def ban_user(self, chat_id: int, user_id: int) -> None:
        self._reply_queue.put(
            _Task("ban_chat_member", {"chat_id": chat_id, "user_id": user_id})
        )

    def _handle_message_queue(self, queue):
        # TODO: Implement messages handling via queue
        pass

    def _send_message_queue(self, queue: Queue):
        while True:
            task = queue.get()
            try:
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

    def log(self, msg: str, severity: str = "info") -> None:
        print(f"BOT [{severity}]: {msg}")

    def _chat_member_joins(self, message: telebot.types.Message):
        # Hotfix for handling messages from groups when storage does not have info
        # about where bot is member. TODO Make pretty solution
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
            if confirm_code is None or not len(confirm_code):
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
                self.log(
                    "Unhandled error in plugin {plugin.__class__.__name__}:\n{e}",
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
        # Hotfix for handling messages from groups when storage does not have info
        # about where bot is member. TODO Make pretty solution
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
