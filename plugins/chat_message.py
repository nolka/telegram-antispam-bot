"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat messages received
"""

import telebot

import bot
from plugins import PLUGIN_NEW_CHAT_MESSAGE, AbstractPlugin
from plugins.spam_filter import KIND_NORMAL, KIND_SPAM, SpamFilter
from storage import AbstractStorage

REACTION_POSSIBLE_SPAM = "🤔"


class ChatMessagePlugin(AbstractPlugin):
    """Base class for messaging plugins"""

    plugin_type = PLUGIN_NEW_CHAT_MESSAGE


class TestPlugin(ChatMessagePlugin):
    """
    Test plugin for messages, just print information in lo about message has ben received
    """

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        self._logger.info(f"Received message {message.from_user.full_name}: {message.text}")


class SpamDetectorPlugin(ChatMessagePlugin):
    known_commands: dict = {
        "+spam": "_add_to_spam",
        "-spam": "_delete_from_spam",
        "!list_spam": "_list_spam",
        "!list_normal": "_list_normal",
    }

    def __init__(self, logger, storage: AbstractStorage) -> None:
        super().__init__(logger)
        self._storage: AbstractStorage = storage

        self._logger.info("Loading spamfilter...")
        self._spam_filter = SpamFilter(logger.get_child_logger("SpamFilter"), storage)
        self._logger.info("Spamfilter loaded")

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        if message.text.startswith(("+", "-", "!")):
            self._handle_command(engine, message)
            return None

        check_result = self._spam_filter.is_spam(message.text)
        self._logger.info(f"check result: {check_result}")
        if check_result.is_spam:
            self._logger.warning(
                f"spam (possibility: {check_result.possibility}) detected from user: {message.from_user.id}({message.from_user.first_name}): {message.text}"
            )
            if check_result.possibility >= 0.9:
                engine.ban_chat_member(message.chat.id, message.from_user.id, True)
                return

            engine.set_message_reaction(message.chat.id, message.id, REACTION_POSSIBLE_SPAM)

    def exit(self):
        self._logger.warning("Saving database...")
        self._spam_filter.save()
        self._logger.warning("   ... Success")

    def _handle_command(self, engine: bot.Engine, message: telebot.types.Message):
        if not engine.is_user_admin(message.from_user.id):
            return

        self._logger.info(f"handling cmd: {message.text}")
        if message.reply_to_message is not None:
            self._logger.info(f"in reply to message: {message.reply_to_message.text}")
        handler_name = self.known_commands.get(message.text, None)
        if handler_name is None:
            self._logger.error(f"No handler set for command: {message.text}")
            return

        handler = getattr(self, handler_name, None)
        if handler is None:
            self._logger.error(f"Handler not implemented for command: {message.text}")
            return

        handler(engine, message)

    def _add_to_spam(self, engine: bot.Engine, message: telebot.types.Message) -> None:
        if not hasattr(message, "reply_to_message"):
            self._logger.error("Cannot mark message as spambecause no 'reply_to_message' exists")
            return

        self._spam_filter.add_spam_phrase(message.reply_to_message.text)

        group_id: int = message.reply_to_message.chat.id
        user_id: int = message.reply_to_message.from_user.id

        engine.delete_message(group_id, message.id)
        engine.delete_message(group_id, message.reply_to_message.id)
        engine.kick_chat_member(group_id, user_id)
        self._logger.info(f"User {user_id} was kicked from group {group_id} because spam detected")

    def _delete_from_spam(self, engine: bot.Engine, message: telebot.types.Message) -> None:
        self._spam_filter.del_spam_phrase(message.reply_to_message.text)
        self._logger.info(f"Phrase removed from spam: {message.reply_to_message.text}")

    def _list_spam(self, engine: bot.Engine, message: telebot.types.Message):
        for h, t in self._spam_filter.get_messages_dict(KIND_SPAM).items():
            self._logger.info(f"{h} -> {t}")

    def _list_normal(self, engine: bot.Engine, message: telebot.types.Message):
        for h, t in self._spam_filter.get_messages_dict(KIND_NORMAL).items():
            self._logger.info(f"{h} -> {t}")
