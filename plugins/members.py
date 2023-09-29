"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat member joins to group
"""
from threading import Timer
from random import choice, seed, shuffle

import requests
import telebot

import bot
from views import messages
from plugins import AbstractPlugin, PLUGIN_NEW_CHAT_MEMBER
from entities.delayed_response import DelayedResponseQueue

_CAS_HOST = "https://api.cas.chat/check"


class MemberPlugin(AbstractPlugin):
    """ Base class for new member plugins """
    plugin_type = PLUGIN_NEW_CHAT_MEMBER


class CASBan(MemberPlugin):
    """
    Check if member is already banned by combot service
    """

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        for new_member in message.new_chat_members:
            self._logger.info(f"Checking CAS ban for user {new_member.id} in group {message.chat.id}")
            response = requests.get(_CAS_HOST, params={"user_id": new_member.id})
            if response.status_code != 200:
                return None

            json = response.json()
            if not json["ok"]:
                return None

            self._logger.info(
                f"CAS ban for {new_member.username}, {new_member.full_name}",
                module_name="CASBan",
            )
            engine.ban_user(message.chat.id, new_member.id)

            return True


class AntispamVerification(MemberPlugin):
    """
    Performs antispam verification. Kicks user from group if they not passed verification
    through emoji
    """

    emojies = ["❤️", "🙈", "💋", "😭", "😡", "😚"]

    def __init__(self, logger, kick_after_sec: int = 180) -> None:
        super().__init__(logger)
        self.kick_after_sec = kick_after_sec

    def execute(self, engine: bot.Engine, message: telebot.types.Message) -> None | bool:
        for new_member in message.new_chat_members:
            if new_member.username == engine.bot_username:
                engine.on_bot_added_to_group(message.chat.id)
                continue

            if engine.storage.is_user_confirmed(message.chat.id, new_member.id):
                continue

            confirm_code = engine.storage.get_user_confirm_code(
                message.chat.id, new_member.id
            )
            if confirm_code is None or not confirm_code:
                seed()
                confirm_code = choice(self.emojies)
                engine.storage.set_user_confirm_code(
                    message.chat.id, new_member.id, confirm_code
                )

            response = engine.send_message(
                reply_to=DelayedResponseQueue(),
                chat_id=message.chat.id,
                text=messages.render_new_member_joined_message(
                    {
                        "new_member": new_member,
                        "confirm_code": confirm_code,
                    },
                ),
                parse_mode="markdownV2",
                reply_markup=self._get_emoji_keyboard(),
            )

            timer = Timer(
                self.kick_after_sec,
                self.kick_inactive,
                args=(engine, message.chat.id, new_member.id, response.get().id),
            )
            timer.start()

    def _get_emoji_keyboard(self) -> telebot.types.InlineKeyboardMarkup:
        shuffle(self.emojies)
        return telebot.types.InlineKeyboardMarkup(
            [
                [
                    telebot.types.InlineKeyboardButton(x, callback_data=x)
                    for x in self.emojies
                ]
            ]
        )

    def kick_inactive(
        self, engine: bot.Engine, group_id: int, user_id: int, captha_msg_id: int
    ) -> None:
        if engine.is_user_confirmed(group_id, user_id):
            return

        engine.kick_chat_member(group_id, user_id)
        self._logger.info(f"User {user_id} was kicked from group {group_id} because not confirmed")
        engine.delete_message(group_id, captha_msg_id)
