"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat messages received
"""
import telebot

import bot
from plugins import PLUGIN_NEW_CHAT_MESSAGE, AbstractPlugin


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
        self._logger.info("Received message")
