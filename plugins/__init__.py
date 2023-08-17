from abc import ABC, abstractmethod

import telebot

from bot import Engine


class AbstractMessage(ABC):

    @abstractmethod
    def execute(self, bot: Engine, message: telebot.types.Message) -> None | bool:
        pass
