"""The main function for launching the bot."""
import os
import signal
import sys

import telebot
from dotenv import load_dotenv

from bot import Engine
from logger import Logger
from plugins.members import CASBan, AntispamVerification, RemoveMemberJoinedMessage
from plugins.chat_message import TestPlugin
from storage import FileSystem
from metrics import start_metrics_server, BotMetrics


def main():
    """
    Main entrypoint
    """

    load_dotenv()
    start_metrics_server(
        int(os.getenv("METRICS_PORT", "9090")), os.getenv("METRICS_HOST", "127.0.0.1")
    )

    bot_metrics = BotMetrics()
    storage = FileSystem(
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "storage")
    )
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    logger = Logger("BOT")
    engine = Engine(
        os.getenv("TELEGRAM_BOT_USERNAME"), bot, bot_metrics, storage, logger
    )
    engine.add_plugin(CASBan(Logger("CasBan")))
    engine.add_plugin(
        AntispamVerification(
            Logger("AntispamVerification"),
            engine,
            int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", "180")),
        )
    )
    engine.add_plugin(RemoveMemberJoinedMessage(Logger("RemoveMemberJoinedMessage")))
    engine.add_plugin(TestPlugin(Logger("TestPlugin")))

    def handle_ctrlc(
            signum,  # pylint: disable=W0613
            frame,  # pylint: disable=W0613
    ):
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
