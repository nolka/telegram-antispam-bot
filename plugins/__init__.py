from __future__ import annotations

from abc import ABC, abstractmethod

import telebot

import bot
from logger import Logger

PLUGIN_NEW_CHAT_MESSAGE = 1
PLUGIN_NEW_CHAT_MEMBER = 2


class AbstractPlugin(ABC):
    """ Base class for all of plugins """

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    @abstractmethod
    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        pass

    def log(self, msg: str, severity: str = "info") -> None:
        match severity:
            case "error":
                self._logger.error(msg)
            case _:
                self._logger.info(msg)
