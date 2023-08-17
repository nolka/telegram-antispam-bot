from bot import Engine
import os
import telebot
import signal
from storage import FileSystem
from plugins.members import CASBan, KickUserNotSolvedCaptha
<<<<<<< Updated upstream
from dotenv import load_dotenv, dotenv_values
=======
from dotenv import load_dotenv
from logger import Logger
>>>>>>> Stashed changes


def main():
    def handle_ctrlc(signum, frame):
        print("\n*** Ctrl-c was pressed. Stopping bot... ")
        engine.stop()
        exit(0)

    load_dotenv()
    signal.signal(signal.SIGINT, handle_ctrlc)
    storage = FileSystem(os.path.join(os.getcwd(), "storage"))
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    logger = Logger("BOT")
    engine = Engine(os.getenv("TELEGRAM_BOT_USERNAME"), bot, storage, logger)
    engine.add_plugin(CASBan())
    engine.add_plugin(KickUserNotSolvedCaptha(int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", 180))))
    engine.start()


if __name__ == "__main__":
    main()
