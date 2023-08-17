import os
import signal
import sys

import telebot
from dotenv import load_dotenv

from bot import Engine
from logger import Logger
from plugins.members import CASBan, KickUserNotSolvedCaptha
from storage import FileSystem


def main():
    """
    Main entrypoint
    """

    def handle_ctrlc(signum, frame):
        """
        Function for handling Ctrl+C keys pressed
        """
        print("\n*** Ctrl-c was pressed. Stopping bot... ")
        engine.stop()
        sys.exit(0)

    load_dotenv()
    signal.signal(signal.SIGINT, handle_ctrlc)
    storage = FileSystem(os.path.join(os.getcwd(), "storage"))
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    logger = Logger("BOT")
    engine = Engine(os.getenv("TELEGRAM_BOT_USERNAME"), bot, storage, logger)
    engine.add_plugin(CASBan())
    engine.add_plugin(
        KickUserNotSolvedCaptha(
            int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", "180"))
        )
    )
    engine.start()


if __name__ == "__main__":
    main()
