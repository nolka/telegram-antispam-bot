from plugins import AbstractMessage
import requests
from bot import Engine
import telebot
from threading import Timer

_cas_host = "https://api.cas.chat/check"


class CASBan(AbstractMessage):
    def execute(self, bot: Engine, message: telebot.types.Message) -> None | bool:
        for new_member in message.new_chat_members:
<<<<<<< Updated upstream
            bot.log(f"Checking CAS ban for user {new_member.id}")
            response = requests.get(
                _cas_host, params={"user_id": new_member.id}
            )
=======
            bot.log(f"Checking CAS ban for user {new_member.id}", module_name="CASBan")
            response = requests.get(_cas_host, params={"user_id": new_member.id})
>>>>>>> Stashed changes
            if response.status_code != 200:
                return

            json = response.json()
            if not json["ok"]:
                return

            bot.log(
<<<<<<< Updated upstream
                f"CAS ban for {new_member.username}, {new_member.full_name}")
=======
                f"CAS ban for {new_member.username}, {new_member.full_name}",
                module_name="CASBan",
            )
>>>>>>> Stashed changes
            bot.ban_user(message.chat.id, new_member.id)

            return True


class KickUserNotSolvedCaptha(AbstractMessage):
    def __init__(self, kick_after_sec: int = 180) -> None:
        super().__init__()
        self.kick_after_sec = kick_after_sec

    def execute(self, bot: Engine, message: telebot.types.Message) -> None | bool:
        for new_member in message.new_chat_members:
            timer = Timer(self.kick_after_sec, self.kick_inactive, args=(bot, message.chat.id, new_member.id))
            timer.start()
    
    def kick_inactive(self, bot: Engine, group_id: int, user_id: int) -> None:
        if bot.is_user_confirmed(group_id, user_id):
                return
        
        bot.kick_chat_member(group_id, user_id)
<<<<<<< Updated upstream
        bot.log(f"User {user_id} was kicked from group {group_id} because not confirmed")
        
=======
        bot.log(
            f"User {user_id} was kicked from group {group_id} because not confirmed",
            module_name="KickUserNotSolvedCaptha",
        )
>>>>>>> Stashed changes
