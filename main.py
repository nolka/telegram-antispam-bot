import os  # С импротами все понятно, кроме самих модулей, это я почитаю
import signal
import sys

import telebot
# линтер ругается, на то, что не может импортировать телебот, хотя pip list говорит
# что установлен telebot 0.0.5
from dotenv import load_dotenv
# линтер ругается, на то, что не может импортировать dotenv, хотя pip list говорит
# что установлен python-dotenv 1.0.0

from bot import Engine  # Тут мы импортируем Engine из bot.py и т.д. ниже по коду
from logger import Logger
from plugins.members import CASBan, AntispamVerification
from plugins.chat_message import TestPlugin
from storage import FileSystem


def main():
    """
    Main entrypoint
    """
# Выше так называемый Docstring, у нас его принято оформлять иначе.
# """Main entrypoint.""" - правильно
# При этом в классах после докстринга есть пробел, в функциях нет пробела.

    load_dotenv()
    storage = FileSystem(os.path.join
                         (os.path.dirname(os.path.abspath(sys.argv[0])), "storage")
                         )
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    logger = Logger("BOT")
    engine = Engine(os.getenv("TELEGRAM_BOT_USERNAME"), bot, storage, logger)
    engine.add_plugin(CASBan(Logger("CasBan")))
    engine.add_plugin(
        AntispamVerification(
            Logger("AntispamVerification"),
            int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", "180"))
        )
    )
    engine.add_plugin(TestPlugin(Logger("TestPlugin")))

    def handle_ctrlc(signum, frame):  # Эта функция тормозит бота по нажатию Ctrl+C
        # Здесь линтер ругается на не используемые аргументы signum и frame
        # не понимаю, для чего здесь аргументы
        """
        Function for handling Ctrl+C keys pressed
        """
        print("\n*** Ctrl-c was pressed. Stopping bot... ")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_ctrlc)
    signal.signal(signal.SIGTERM, handle_ctrlc)

    engine.start()


if __name__ == "__main__":
    main()
