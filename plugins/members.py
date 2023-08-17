"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat member joins to group
"""
from threading import Timer

import requests
import telebot

from bot import Engine
from plugins import AbstractMessage

_CAS_HOST = "https://api.cas.chat/check"


class CASBan(AbstractMessage):
    """
    Check if member is already banned by combot service
    """
    def execute(self, bot: Engine, message: telebot.types.Message) -> None | bool:
        for new_member in message.new_chat_members:

            bot.log(f"Checking CAS ban for user {new_member.id}", module_name="CASBan")
            response = requests.get(_CAS_HOST, params={"user_id": new_member.id})
            if response.status_code != 200:
                return None

            json = response.json()
            if not json["ok"]:
                return None

            bot.log(
                f"CAS ban for {new_member.username}, {new_member.full_name}",
                module_name="CASBan",
            )
            bot.ban_user(message.chat.id, new_member.id)

            return True


class KickUserNotSolvedCaptha(AbstractMessage):
    """
    Kick user from group if them is not passed antispam validation
    """
    def __init__(self, kick_after_sec: int = 180) -> None:
        super().__init__()
        self.kick_after_sec = kick_after_sec

    def execute(self, bot: Engine, message: telebot.types.Message) -> None | bool:
        for new_member in message.new_chat_members:
            timer = Timer(
                self.kick_after_sec,
                self.kick_inactive,
                args=(bot, message.chat.id, new_member.id),
            )
            timer.start()

    def kick_inactive(self, bot: Engine, group_id: int, user_id: int) -> None:
        if bot.is_user_confirmed(group_id, user_id):
            return

        bot.kick_chat_member(group_id, user_id)
        bot.log(
            f"User {user_id} was kicked from group {group_id} because not confirmed",
            module_name="KickUserNotSolvedCaptha",
        )
