"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat messages received
"""
import telebot

import bot
from storage import AbstractStorage
from plugins import PLUGIN_NEW_CHAT_MESSAGE, AbstractPlugin
from plugins.spam_filter import SpamFilter

REACTION_POSSIBLE_SPAM = "🤔"

class ChatMessagePlugin(AbstractPlugin):
    """ Base class for messaging plugins """
    plugin_type = PLUGIN_NEW_CHAT_MESSAGE


class TestPlugin(ChatMessagePlugin):
    """
    Test plugin for messages, just print information in lo about message has ben received
    """

    def execute(
        self, engine: bot.Engine, message: telebot.types.Message
    ) -> None | bool:
        self._logger.info(f"Received message")

class SpamDetectorPlugin(ChatMessagePlugin):
    known_commands: dict = {
        "+spam": "_add_to_spam",
        "-spam": "_delete_from_spam"
    }

    def __init__(self, logger, storage: AbstractStorage) -> None:
        super().__init__(logger)
        self._storage: AbstractStorage  = storage

        self._logger.info("Loading spamfilter...")
        self._spam_filter = SpamFilter(
            storage.get_spam_messages(),
            storage.get_nonspam_messages()
        )
        self._logger.info("Spamfilter loaded")

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        if message.text.startswith("+"):
            self._handle_command(engine, message)
            return None

        if self._spam_filter.is_spam(message.text):
            self._logger.warning(f"spam detected from user: {message.from_user.id}({message.from_user.first_name}): {message.text}")
            engine.set_message_reaction(message.chat.id, message.id, REACTION_POSSIBLE_SPAM)
            return

        self._storage.add_nonspam_message(message.text)

    def _handle_command(self, engine: bot.Engine, message: telebot.types.Message):
        if not engine.is_user_admin(message.from_user.id):
            return

        self._logger.info(f"handling cmd: {message.text} in reply to message: {message.reply_to_message.text}")
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
            self._logger.error(f"Cannot mark message as spambecause no 'reply_to_message' exists")
            return

        self._storage.add_spam_message(message.reply_to_message.text)
        self._spam_filter.add_spam_phrases(message.reply_to_message.text)

        group_id: int = message.reply_to_message.chat.id
        user_id: int = message.reply_to_message.from_user.id

        engine.delete_message(group_id, message.id)
        engine.delete_message(group_id, message.reply_to_message.id)
        engine.kick_chat_member(group_id, user_id)
        self._logger.info(
            f"User {user_id} was kicked from group {group_id} because spam detected"
        )

    def _delete_from_spam(self, engine: bot.Engine, message: telebot.types.Message) -> None:
        pass
