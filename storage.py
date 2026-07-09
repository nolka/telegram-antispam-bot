"""
Data storage layer. Contains classes for managing bot data, which be used to perform antispam
operations
"""

import codecs
import json
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import select

from db import Connection
from models import (
    Base,
    ConfirmCode,
    ConfirmedUser,
    Group,
    SpamTraining,
)


class AbstractStorage(ABC):
    """
    Interface describing storage class. If you want to add new storage class, you need
    to subclass it from this class and implement all the methods below
    """

    @abstractmethod
    def is_user_confirmed(self, group_id: int, user_id: int) -> bool:
        pass

    @abstractmethod
    def set_user_confirmed(self, group_id: int, user_id: int) -> bool:
        pass

    @abstractmethod
    def set_user_confirm_code(self, group_id: int, user_id: int, confirm_code: str) -> None:
        pass

    @abstractmethod
    def get_user_confirm_code(self, group_id: int, user_id: int) -> str:
        pass

    @abstractmethod
    def on_added_to_group(self, group_id: int) -> None:
        pass

    @abstractmethod
    def get_spam_messages(self) -> list[str]:
        pass

    @abstractmethod
    def save_spam_messages(self, messages: list[str]) -> None:
        pass

    @abstractmethod
    def get_normal_messages(self) -> list[str]:
        pass

    @abstractmethod
    def save_normal_messages(self, messages: list[str]) -> None:
        pass

    @abstractmethod
    def save_message(
        self,
        group_id: int,
        user_id: int,
        msg_id: int,
        msg_type: str,
        text: str | None,
        params: dict | None = None,
    ) -> None:
        pass

    @abstractmethod
    def get_user_message_count(self, group_id: int, user_id: int) -> int:
        """Returns the count of previously sent messages by a user in a specific group."""
        pass


def convert_path(path: str) -> str:
    """
    Platform-independent filesystem paths constructor
    """
    return os.path.join(*os.path.split(path))


def to_path(*args) -> str:
    """
    Make platform-independent filesystem path from array of args
    """
    return os.path.join(*[str(x) for x in args])


def create_storage_dir(path: str) -> None:
    """
    Creates main storage directory for saving data
    """
    os.makedirs(path, exist_ok=True)


class FileSystem(AbstractStorage):
    """
    Implements data storage in filesystem as files and subfolders tree
    """

    confirmed_dir = "confirmed"
    confirm_codes_dir = "confirm_codes"

    groups_list_file = "groups.txt"
    spam_messages_file = "spam_messages.txt"
    nonspam_messages_file = "nonspam_messages.txt"
    ml_data_file = "ml_data.json"

    required_dirs = (confirmed_dir, confirm_codes_dir)

    def __init__(self, path: str, groups_list: set[str] = None):
        self.storage_dir = convert_path(path)
        self.groups_list = set([] if groups_list is None else [str(x) for x in groups_list])

        self._load_groups_list()
        self._create_storage_dir()
        self._create_groups_dir()

    def _load_groups_list(self) -> None:
        if os.path.exists(to_path(self.storage_dir, self.groups_list_file)):
            with codecs.open(to_path(self.storage_dir, self.groups_list_file), "r") as file:
                self.groups_list = {int(x) for x in file.readlines()}

    def _create_storage_dir(self) -> None:
        if not os.path.exists(self.storage_dir):
            create_storage_dir(self.storage_dir)

    def is_user_confirmed(self, group_id: int, user_id: int) -> bool:
        return os.path.exists(to_path(self.storage_dir, group_id, "confirmed", user_id))

    def set_user_confirmed(self, group_id: int, user_id: int) -> bool:
        confirmed_file = to_path(self.storage_dir, str(group_id), "confirmed", str(user_id))
        confirm_code_file = to_path(self.storage_dir, str(group_id), "confirm_codes", str(user_id))
        with codecs.open(confirmed_file, "w", encoding="utf-8") as _:
            try:
                os.unlink(confirm_code_file)
            except FileNotFoundError:
                pass

    def set_user_confirm_code(self, group_id: int, user_id: int, confirm_code: str) -> None:
        file_name = to_path(self.storage_dir, group_id, "confirm_codes", user_id)
        with codecs.open(file_name, "w", encoding="utf-8") as file:
            file.write(confirm_code)

    def get_user_confirm_code(self, group_id: int, user_id: int) -> str | None:
        file_name = to_path(self.storage_dir, group_id, "confirm_codes", user_id)
        try:
            with codecs.open(file_name, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return None

    def on_added_to_group(self, group_id: int) -> None:
        self._create_group_dir(group_id)
        self.groups_list.add(group_id)

        self._save_groups_list()

    def _save_groups_list(self) -> None:
        with codecs.open(
            to_path(self.storage_dir, self.groups_list_file),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.writelines([f"{x}\n" for x in self.groups_list])

    def _create_groups_dir(self) -> None:
        for group_id in self.groups_list:
            self._create_group_dir(group_id)

    def _create_group_dir(self, group_id: int) -> None:
        for dir_path in self.required_dirs:
            create_storage_dir(to_path(self.storage_dir, group_id, dir_path))

    def get_spam_messages(self) -> list[str]:
        with codecs.open(
            to_path(self.storage_dir, self.spam_messages_file), encoding="utf-8"
        ) as fh:
            return fh.readlines()

    def save_spam_messages(self, messages: list[str]) -> None:
        with codecs.open(
            to_path(self.storage_dir, self.spam_messages_file),
            "w",
            encoding="utf-8",
        ) as fh:
            for msg in messages:
                fh.write(msg + "\n")

    def save_normal_messages(self, messages: list[str]) -> None:
        with codecs.open(
            to_path(self.storage_dir, self.nonspam_messages_file),
            "w",
            encoding="utf-8",
        ) as fh:
            for msg in messages:
                fh.write(msg + "\n")

    def get_normal_messages(self) -> list[str]:
        with codecs.open(
            to_path(self.storage_dir, self.nonspam_messages_file),
            "r+",
            encoding="utf-8",
        ) as fh:
            return fh.readlines()

    def save_message(
        self,
        group_id: int,
        user_id: int,
        msg_id: int,
        msg_type: str,
        text: str | None,
        params: dict | None = None,
    ) -> None:
        log_path = to_path(self.storage_dir, "messages.jsonl")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "group_id": group_id,
            "user_id": user_id,
            "msg_id": msg_id,
            "type": msg_type,
            "text": text,
            "params": params,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_user_message_count(self, group_id: int, user_id: int) -> int:
        """Returns the count of previously sent messages by a user in a specific group."""
        log_path = to_path(self.storage_dir, "messages.jsonl")
        if not os.path.exists(log_path):
            return 0

        count = 0
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("group_id") == group_id and entry.get("user_id") == user_id:
                        count += 1
                except json.JSONDecodeError:
                    continue
        return count


class DatabaseStorage(AbstractStorage):
    """
    Implements data storage in PostgreSQL via SQLAlchemy.
    """

    def __init__(self, db_url: str) -> None:
        self._db = Connection(db_url)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create all tables if they don't exist."""
        with self._get_session() as _:
            Base.metadata.create_all(self._db.engine)

    @contextmanager
    def _get_session(self):
        """Yield a database session and guarantee it's closed on exit."""
        session = self._db.new_session()
        try:
            yield session
        finally:
            session.close()

    def is_user_confirmed(self, group_id: int, user_id: int) -> bool:
        with self._get_session() as session:
            result = session.execute(
                select(ConfirmedUser).where(
                    ConfirmedUser.group_id == group_id,
                    ConfirmedUser.user_id == user_id,
                )
            ).scalar_one_or_none()
            return result is not None

    def set_user_confirmed(self, group_id: int, user_id: int) -> bool:
        with self._get_session() as session:
            # Upsert confirmed user
            existing = session.execute(
                select(ConfirmedUser).where(
                    ConfirmedUser.group_id == group_id,
                    ConfirmedUser.user_id == user_id,
                )
            ).scalar_one_or_none()

            if existing:
                session.commit()
                return True

            session.add(ConfirmedUser(group_id=group_id, user_id=user_id))
            session.commit()
            return True

    def set_user_confirm_code(self, group_id: int, user_id: int, confirm_code: str) -> None:
        with self._get_session() as session:
            existing = session.execute(
                select(ConfirmCode).where(
                    ConfirmCode.group_id == group_id,
                    ConfirmCode.user_id == user_id,
                )
            ).scalar_one_or_none()

            if existing:
                existing.code = confirm_code
            else:
                session.add(ConfirmCode(group_id=group_id, user_id=user_id, code=confirm_code))
            session.commit()

    def get_user_confirm_code(self, group_id: int, user_id: int) -> str | None:
        with self._get_session() as session:
            result = session.execute(
                select(ConfirmCode.code).where(
                    ConfirmCode.group_id == group_id,
                    ConfirmCode.user_id == user_id,
                )
            ).scalar_one_or_none()
            return result

    def on_added_to_group(self, group_id: int) -> None:
        with self._get_session() as session:
            existing = session.execute(
                select(Group).where(Group.id == group_id)
            ).scalar_one_or_none()

            if not existing:
                session.add(Group(id=group_id))
                session.commit()

    def get_spam_messages(self) -> list[str]:
        with self._get_session() as session:
            results = (
                session
                .execute(select(SpamTraining.text).where(SpamTraining.is_spam == True))
                .scalars()
                .all()
            )
            return results

    def save_spam_messages(self, messages: list[str]) -> None:
        with self._get_session() as session:
            session.execute(SpamTraining.__table__.delete().where(SpamTraining.is_spam == True))
            for msg in messages:
                text = msg.strip()
                if text:
                    session.add(SpamTraining(text=text, is_spam=True))
            session.commit()

    def get_normal_messages(self) -> list[str]:
        with self._get_session() as session:
            results = (
                session
                .execute(select(SpamTraining.text).where(SpamTraining.is_spam == False))
                .scalars()
                .all()
            )
            return results

    def save_normal_messages(self, messages: list[str]) -> None:
        with self._get_session() as session:
            session.execute(SpamTraining.__table__.delete().where(SpamTraining.is_spam == False))
            for msg in messages:
                text = msg.strip()
                if text:
                    session.add(SpamTraining(text=text, is_spam=False))
            session.commit()

    def save_message(
        self,
        group_id: int,
        user_id: int,
        msg_id: int,
        msg_type: str,
        text: str | None,
        params: dict | None = None,
    ) -> None:
        from models import Message as MessageModel
        from models import User

        with self._get_session() as session:
            # Создаем или обновляем пользователя
            user = session.get(User, user_id)
            if params:
                if user is None:
                    user = User(
                        id=user_id,
                        first_name=params.get("first_name"),
                        last_name=params.get("last_name"),
                        username=params.get("username"),
                    )
                    session.add(user)
                else:
                    user.first_name = params.get("first_name", user.first_name)
                    user.last_name = params.get("last_name", user.last_name)
                    user.username = params.get("username", user.username)
            elif user is None:
                session.add(User(id=user_id))

            # Создаем группу, если ее нет
            group = session.get(Group, group_id)
            if params and group is None:
                group = Group(
                    id=group_id,
                    name=params.get("chat_title"),
                    type=params.get("chat_type"),
                    description=params.get("chat_description"),
                )
                session.add(group)
            elif params and group is not None:
                group.name = params.get("chat_title", group.name)
                group.type = params.get("chat_type", group.type)
                group.description = params.get("chat_description", group.description)
            elif group is None:
                session.add(Group(id=group_id))

            session.add(
                MessageModel(
                    id=msg_id,
                    group_id=group_id,
                    user_id=user_id,
                    type=msg_type,
                    text=text,
                    params=params,
                )
            )
            session.commit()

    def get_user_message_count(self, group_id: int, user_id: int) -> int:
        """Returns the count of previously sent messages by a user in a specific group."""
        from sqlalchemy import func as sql_func

        from models import Message as MessageModel

        with self._get_session() as session:
            # Используем sql_func.count вместо .count() — это генерирует
            # "SELECT count(message.id)" вместо "SELECT count(*) FROM (SELECT ...)"
            count = session.execute(
                select(sql_func.count(MessageModel.id)).where(
                    MessageModel.group_id == group_id,
                    MessageModel.user_id == user_id,
                )
            ).scalar_one_or_none()
            return count or 0
