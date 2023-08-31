from __future__ import annotations

from abc import ABC, abstractmethod

import telebot

import bot

PLUGIN_NEW_CHAT_MESSAGE = 1
PLUGIN_NEW_CHAT_MEMBER = 2


class AbstractPlugin(ABC):

    @abstractmethod
    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        pass
