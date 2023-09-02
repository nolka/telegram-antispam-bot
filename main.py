import os
import signal
import sys

import telebot
from dotenv import load_dotenv

from bot import Engine
from logger import Logger
from plugins.members import CASBan, AntispamVerification
from plugins.chat_message import TestPlugin
from storage import FileSystem


def main():
    """
    Main entrypoint
    """

    load_dotenv()
    storage = FileSystem(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "storage"))
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    logger = Logger("BOT")
    engine = Engine(os.getenv("TELEGRAM_BOT_USERNAME"), bot, storage, logger)
    engine.add_plugin(CASBan())
    engine.add_plugin(
        AntispamVerification(
            int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", "180"))
        )
    )
    engine.add_plugin(TestPlugin())

    def handle_ctrlc(signum, frame):
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
