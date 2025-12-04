"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat messages received
"""

import telebot

import bot
from plugins import PLUGIN_NEW_CHAT_MESSAGE, AbstractPlugin
from plugins.spam_filter import KIND_NORMAL, KIND_SPAM, SpamFilter, SpamMessageCollection
from storage import AbstractStorage

REACTION_POSSIBLE_SPAM = "🤔"
REACTION_ASSERT_SPAM = "💩"


class ChatMessagePlugin(AbstractPlugin):
    """Base class for messaging plugins"""

    plugin_type = PLUGIN_NEW_CHAT_MESSAGE


class MessageLoggerPlugin(ChatMessagePlugin):
    """
    Test plugin for messages, just print information in lo about message has ben received
    """

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        print(message.__class__)
        msg_data = {
            "user_name": message.from_user.full_name,
            "user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "chat_title": message.chat.title,
            "type": message.chat.type,
        }

        if message.text:
            msg_data["text"] = message.text

        self._logger.info(
            f"Received message: {'\n'.join([f'  {k}: {v}' for k, v in msg_data.items()])}"
        )

    def execute_reaction(
        self, engine: bot.Engine, message: telebot.types.MessageReactionUpdated
    ) -> None | bool:
        pass


class SpamDetectorPlugin(ChatMessagePlugin):
    known_commands: dict = {
        "+spam": "_add_to_spam",
        "-spam": "_delete_from_spam",
        "!list_spam": "_list_spam",
        "!list_normal": "_list_normal",
    }

    def __init__(
        self, logger, storage: AbstractStorage, instant_ban_predict_value: float = 0.9
    ) -> None:
        super().__init__(logger)
        self._storage: AbstractStorage = storage
        self._instant_ban_predict_value = instant_ban_predict_value

        self._logger.info("Loading spamfilter...")
        self._spam_filter = SpamFilter(logger.get_child_logger("SpamFilter"), storage)
        self._logger.info("Spamfilter loaded")
        self._spam_msg_map = SpamMessageCollection()

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        if message.text.startswith(("+", "-", "!")):
            self._handle_command(engine, message)
            return None

        check_result = self._spam_filter.is_spam(message.text)
        self._logger.info(f"check result: {check_result}")
        if check_result.is_spam:
            engine.set_message_reaction(message.chat.id, message.id, REACTION_POSSIBLE_SPAM)
            engine.metrics.inc_spam_message_detected_total(message.chat.id, message.from_user.id)
            self._logger.warning(
                f"spam (possibility: {check_result.possibility}) detected from user: {message.from_user.id}({message.from_user.first_name}): {message.text}"
            )

            if check_result.possibility >= self._instant_ban_predict_value:
                engine.ban_chat_member(message.chat.id, message.from_user.id, True)
                # self._spam_filter.add_spam_phrase(message.text)
                self._logger.info(
                    f"User {message.from_user.id}({message.from_user.first_name}) banned because possibility of spam is greather than {self._instant_ban_predict_value}"
                )
                return

            self._spam_msg_map.add_score(
                message.chat.id, message.message_id, message.from_user.id, 0
            )

    def execute_reaction(
        self, engine: bot.Engine, message: telebot.types.MessageReactionUpdated
    ) -> None | bool:
        if not self._spam_msg_map.has_item(message.chat.id, message.message_id, message.user.id):
            return

        for reaction in message.new_reaction:
            if reaction.emoji == REACTION_ASSERT_SPAM:
                spam_score = self._spam_msg_map.add_score(
                    message.chat.id, message.message_id, message.user.id
                )
                self._logger.info(f"Spam score for message: {spam_score}")

    def exit(self):
        self._logger.warning("Saving database...")
        self._spam_filter.save()
        self._logger.warning("   ... Success")

    def _handle_command(self, engine: bot.Engine, message: telebot.types.Message):
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

        spam_text = message.reply_to_message.text

        group_id: int = message.reply_to_message.chat.id
        user_id: int = message.reply_to_message.from_user.id

        if not engine.is_user_admin(message.from_user.id):
            self._logger.error("Not removing user because command not from admin")
            return
        engine.delete_message(group_id, message.id)
        engine.delete_message(group_id, message.reply_to_message.id)
        engine.kick_chat_member(group_id, user_id)
        self._logger.info(f"User {user_id} was kicked from group {group_id} because spam detected")
        self._spam_filter.add_spam_phrase(spam_text)
        engine.metrics.inc_spam_message_added_total(group_id, user_id)

    def _delete_from_spam(self, engine: bot.Engine, message: telebot.types.Message) -> None:
        if not engine.is_user_admin(message.from_user.id):
            return

        self._spam_filter.del_spam_phrase(message.reply_to_message.text)
        self._logger.info(f"Phrase removed from spam: {message.reply_to_message.text}")

    def _list_spam(self, engine: bot.Engine, message: telebot.types.Message) -> None:
        if not engine.is_user_admin(message.from_user.id):
            return

        for h, t in self._spam_filter.get_messages_dict(KIND_SPAM).items():
            self._logger.info(f"{h} -> {t}")

    def _list_normal(self, engine: bot.Engine, message: telebot.types.Message) -> None:
        if not engine.is_user_admin(message.from_user.id):
            return

        for h, t in self._spam_filter.get_messages_dict(KIND_NORMAL).items():
            self._logger.info(f"{h} -> {t}")
