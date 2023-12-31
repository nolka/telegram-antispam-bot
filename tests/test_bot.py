import unittest
from contextlib import contextmanager
from unittest.mock import Mock

from bot import Engine


@contextmanager
def create_bot():
    telebot_mock = Mock()
    storage_mock = Mock()
    logger = Mock()
    metrics = Mock()
    bot = Engine("test_bot", telebot_mock, metrics, storage_mock, logger)

    yield bot, telebot_mock, storage_mock


class TestBot(unittest.TestCase):
    def test_start_and_stop(self):
        with create_bot() as (bot, telebot_mock, _):
            bot.start()
            bot.stop()

            telebot_mock.infinity_polling.assert_called_once()
            telebot_mock.stop_bot.assert_called_once()

    def test_methods(self):
        with create_bot() as (bot, telebot_mock, _):
            bot.start()

            bot.ban_user(1, 1)
            bot.delete_message(1, 1)
            bot.kick_chat_member(1, 1)
            bot.send_message(**{"a": "b"})

            bot.stop()

            telebot_mock.ban_chat_member.assert_called_once_with(chat_id=1, user_id=1)
            telebot_mock.delete_message.assert_called_once_with(chat_id=1, message_id=1)
            telebot_mock.kick_chat_member.assert_called_once_with(chat_id=1, user_id=1)
            telebot_mock.send_message.assert_called_once_with(**{"a": "b"})
