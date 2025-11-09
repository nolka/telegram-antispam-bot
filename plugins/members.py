"""
This module contains user-defined plugins which can be plugged into bot to handle events
when new chat member joins to group
"""
from threading import Timer
from random import choice, seed, shuffle
from collections import defaultdict

import requests
import telebot

import bot
from views import messages
from plugins import AbstractPlugin, PLUGIN_NEW_CHAT_MEMBER
from entities.delayed_response import DelayedResponseQueue

_CAS_HOST = "https://api.cas.chat/check"


class MemberPlugin(AbstractPlugin):
    """Base class for new member plugins"""

    plugin_type = PLUGIN_NEW_CHAT_MEMBER


class CASBan(MemberPlugin):
    """
    Check if member is already banned by combot service
    """

    req_timeout = 3

    def execute(
        self, engine: bot.Engine, message: telebot.types.Message
    ) -> None | bool:
        for new_member in message.new_chat_members:
            self._logger.info(
                f"Checking CAS ban for user {new_member.id} in group {message.chat.id}"
            )
            response = requests.get(
                _CAS_HOST, params={"user_id": new_member.id}, timeout=self.req_timeout
            )
            if response.status_code != 200:
                return None

            json = response.json()
            if not json.get("ok", False):
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

    emojies = {
        "❤️": "Сердце",
        "🙈": "Обезъянка",
        "💋": "Губки",
        "😭": "Плачущий смайл",
        "😡": "Злой смайл",
        "🐶": "Песик",
    }

    def __init__(self, logger, engine: bot.Engine, kick_after_sec: int = 180) -> None:
        super().__init__(logger)
        self.engine = engine
        self.kick_after_sec = kick_after_sec
        self.active_timers = defaultdict(list)

        self.engine.add_callback_query_handler(self._user_selected_answer, func=None)

    def execute(
        self, engine: bot.Engine, message: telebot.types.Message
    ) -> None | bool:
        for new_member in message.new_chat_members:
            if new_member.username == engine.bot_username:
                engine.on_bot_added_to_group(message.chat.id)
                self.log(f"The bot was added to group: {message.chat.title}")
                continue

            if engine.storage.is_user_confirmed(message.chat.id, new_member.id):
                self.log(
                    f"User {new_member.id} -> {new_member.full_name} is already confirmed."
                    + "Skip Verification"
                )
                continue

            confirm_text = None
            confirm_code = engine.storage.get_user_confirm_code(
                message.chat.id, new_member.id
            )
            if confirm_code is None or not confirm_code:
                confirm_code = self._generate_confirm_code()
                engine.storage.set_user_confirm_code(
                    message.chat.id, new_member.id, confirm_code
                )
            if not confirm_text:
                confirm_text = self.emojies[confirm_code]

            response = engine.send_message(
                reply_to=DelayedResponseQueue(),
                chat_id=message.chat.id,
                text=messages.render_new_member_joined_message(
                    {
                        "new_member": new_member,
                        "confirm_text": confirm_text,
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
            self.active_timers[(message.chat.id, new_member.id)].append(timer)

    def _generate_confirm_code(self) -> str:
        seed()
        return choice(list(self.emojies))

    def _get_emoji_keyboard(self) -> telebot.types.InlineKeyboardMarkup:
        variants = list(self.emojies)
        shuffle(variants)
        return telebot.types.InlineKeyboardMarkup(
            [
                [
                    telebot.types.InlineKeyboardButton(x, callback_data=f"verify_{x}")
                    for x in variants
                ]
            ]
        )

    def _user_selected_answer(self, callback: telebot.types.CallbackQuery) -> None:
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id

        member_answer = callback.data.split("_")
        if len(member_answer) != 2:
            self.log(f"Error parsing reply callback data: {callback.data}")
            return

        if member_answer[0] != "verify":
            return

        answer = member_answer[1]

        if (
            not self.engine.storage.is_user_confirmed(chat_id, user_id)
            and self.engine.storage.get_user_confirm_code(chat_id, user_id) == answer
        ):
            self.log(f"User {user_id}: {callback.from_user.full_name} solved captha")
            self.engine.storage.set_user_confirmed(chat_id, user_id)
            self.engine.delete_message(chat_id=chat_id, message_id=callback.message.id)
            self.engine.metrics.inc_captha_solved_total(answer)
            self._cleanup_user_timers(chat_id, user_id)
        else:
            self.log(
                f"User {user_id}:  {callback.from_user.full_name} selected "
                + f"incorrect value {answer}"
            )

    def kick_inactive(
        self, engine: bot.Engine, group_id: int, user_id: int, captha_msg_id: int
    ) -> None:
        """Removes chat member if they does not pressed validation button"""
        if engine.storage.is_user_confirmed(group_id, user_id):
            self._cleanup_user_timers(group_id, user_id)
            return

        engine.kick_chat_member(group_id, user_id)
        self._logger.info(
            f"User {user_id} was kicked from group {group_id} because not confirmed"
        )
        engine.delete_message(group_id, captha_msg_id)
        self._cleanup_user_timers(group_id, user_id)

    def _cleanup_user_timers(self, group_id: int, user_id: int) -> None:
        """Clean up all timers for a specific user"""
        timers = self.active_timers.get((group_id, user_id), [])
        for timer in timers:
            if timer and timer.is_alive():
                timer.cancel()

        if (group_id, user_id) in self.active_timers:
            del self.active_timers[(group_id, user_id)]


class RemoveMemberJoinedMessage(MemberPlugin):
    """Performs removing message about new member joined"""

    def execute(
        self, engine: bot.Engine, message: telebot.types.Message
    ) -> None | bool:
        engine.delete_message(message.chat.id, message.id)
