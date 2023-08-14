from abc import abstractmethod, ABC
from bot import Engine
import telebot

class AbstractMessage(ABC):

    @abstractmethod
    def execute(self, bot: Engine, message: telebot.types.Message) -> None | bool:
        pass