from bot import Engine
import os
import telebot
from storage import FileSystem
from plugins.members import CASBan, KickUserNotSolvedCaptha
from dotenv import load_dotenv, dotenv_values


def main():
    load_dotenv()
    storage = FileSystem(os.path.join(os.getcwd(), "storage"))
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    engine = Engine(os.getenv("TELEGRAM_BOT_USERNAME"), bot, storage)
    engine.add_plugin(CASBan())
    engine.add_plugin(KickUserNotSolvedCaptha(int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", 180))))
    engine.start()


if __name__ == "__main__":
    main()
