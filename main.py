"""The main function for launching the bot."""

import argparse
import os
import signal
import sys

import telebot
from dotenv import load_dotenv

from bot import Engine
from logger import Logger
from metrics import BotMetrics, start_metrics_server
from plugins.chat_message import MessageLoggerPlugin, SpamDetectorPlugin
from plugins.members import AntispamVerification, CASBan, RemoveMemberJoinedMessage
from storage import DatabaseStorage, FileSystem
from utils.db import get_postgres_dsn

STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "storage")


def migrate_file_storage_to_db() -> None:
    """
    Migrate data from FileSystem storage to DatabaseStorage.
    Reads all data from the file-based storage and writes it to the database.
    """
    fs_storage = FileSystem(STORAGE_PATH)
    db_url = get_postgres_dsn()
    if not db_url:
        print("Error: POSTGRES_DSN is not set. Cannot migrate to database.")
        return

    db_storage = DatabaseStorage(db_url)

    print("Starting migration from file storage to database...")

    # Migrate groups
    for group_id in fs_storage.groups_list:
        db_storage.on_added_to_group(group_id)
    print(f"Migrated {len(fs_storage.groups_list)} groups")

    # Migrate confirmed users and confirm codes
    confirmed_count = 0
    code_count = 0
    for group_id in fs_storage.groups_list:
        group_dir = os.path.join(fs_storage.storage_dir, str(group_id))

        # Confirmed users - each file in confirmed/ is a user_id
        confirmed_dir = os.path.join(group_dir, "confirmed")
        if os.path.isdir(confirmed_dir):
            for user_id_file in os.listdir(confirmed_dir):
                user_id = int(user_id_file)
                db_storage.set_user_confirmed(group_id, user_id)
                confirmed_count += 1

        # Confirm codes - each file in confirm_codes/ contains a code
        codes_dir = os.path.join(group_dir, "confirm_codes")
        if os.path.isdir(codes_dir):
            for user_id_file in os.listdir(codes_dir):
                user_id = int(user_id_file)
                code_path = os.path.join(codes_dir, user_id_file)
                with open(code_path, "r", encoding="utf-8") as f:
                    code = f.read().strip()
                if code:
                    db_storage.set_user_confirm_code(group_id, user_id, code)
                    code_count += 1

    print(f"Migrated {confirmed_count} confirmed users and {code_count} confirm codes")

    # Migrate spam messages
    spam_msgs = fs_storage.get_spam_messages()
    db_storage.save_spam_messages(spam_msgs)
    print(f"Migrated {len(spam_msgs)} spam messages")

    # Migrate normal messages
    normal_msgs = fs_storage.get_normal_messages()
    db_storage.save_normal_messages(normal_msgs)
    print(f"Migrated {len(normal_msgs)} normal messages")

    print("Migration completed successfully!")


def _create_storage():
    """Create appropriate storage based on environment configuration."""
    db_url = get_postgres_dsn()
    if db_url:
        return DatabaseStorage(db_url)
    else:
        return FileSystem(STORAGE_PATH)


def main():
    """
    Main entrypoint
    """

    start_metrics_server(
        int(os.getenv("METRICS_PORT", "9090")), os.getenv("METRICS_HOST", "127.0.0.1")
    )

    bot_metrics = BotMetrics()
    storage = _create_storage()
    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
    logger = Logger("BOT")
    engine = Engine(os.getenv("TELEGRAM_BOT_USERNAME"), bot, bot_metrics, storage, logger)
    engine.add_admins(os.getenv("BOT_ADMINS"))
    engine.add_plugin(CASBan(Logger("CasBan")))
    engine.add_plugin(
        AntispamVerification(
            Logger("AntispamVerification"),
            engine,
            int(os.getenv("PLUGIN_KICK_NOT_CONFIRMED_USER_AFTER", "180")),
        )
    )
    engine.add_plugin(RemoveMemberJoinedMessage(Logger("RemoveMemberJoinedMessage")))
    engine.add_plugin(
        SpamDetectorPlugin(
            Logger("SpamDetectorPlugin"),
            storage,
            os.getenv("PLUGIN_SPAM_DETECTOR_BAN_TRESHOLD", 0.9),
        )
    )
    engine.add_plugin(MessageLoggerPlugin(Logger("MessageLoggerPlugin")))

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
    load_dotenv()

    parser = argparse.ArgumentParser(description="Telegram Antispam Bot")
    parser.add_argument(
        "--migrate-file-storage-to-db",
        action="store_true",
        help="Migrate data from file storage to database",
    )
    args = parser.parse_args()

    if args.migrate_file_storage_to_db:
        migrate_file_storage_to_db()
    else:
        main()
