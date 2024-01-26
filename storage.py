"""
Data storage layer. Contains classes for managing bot data, which be used to perform antispam
operations
"""

import os
from abc import ABC, abstractmethod
import codecs


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
    def set_user_confirm_code(
        self, group_id: int, user_id: int, confirm_code: str
    ) -> None:
        pass

    @abstractmethod
    def get_user_confirm_code(self, group_id: int, user_id: int) -> str:
        pass

    @abstractmethod
    def on_added_to_group(self, group_id: int) -> None:
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

    required_dirs = (confirmed_dir, confirm_codes_dir)

    def __init__(self, path: str, groups_list: set[str] = None):
        self.storage_dir = convert_path(path)
        self.groups_list = set(
            [] if groups_list is None else [str(x) for x in groups_list]
        )

        self._load_groups_list()
        self._create_storage_dir()
        self._create_groups_dir()

    def _load_groups_list(self) -> None:
        if os.path.exists(to_path(self.storage_dir, self.groups_list_file)):
            with codecs.open(
                to_path(self.storage_dir, self.groups_list_file), "r"
            ) as file:
                self.groups_list = {int(x) for x in file.readlines()}

    def _create_storage_dir(self) -> None:
        if not os.path.exists(self.storage_dir):
            create_storage_dir(self.storage_dir)

    def is_user_confirmed(self, group_id: int, user_id: int) -> bool:
        return os.path.exists(to_path(self.storage_dir, group_id, "confirmed", user_id))

    def set_user_confirmed(self, group_id: int, user_id: int) -> bool:
        confirmed_file = to_path(
            self.storage_dir, str(group_id), "confirmed", str(user_id)
        )
        confirm_code_file = to_path(
            self.storage_dir, str(group_id), "confirm_codes", str(user_id)
        )
        with codecs.open(confirmed_file, "w", encoding="utf-8") as _:
            try:
                os.unlink(confirm_code_file)
            except FileNotFoundError:
                pass

    def set_user_confirm_code(
        self, group_id: int, user_id: int, confirm_code: str
    ) -> None:
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
            to_path(self.storage_dir, self.groups_list_file), "w", encoding="utf-8"
        ) as handle:
            handle.writelines([f"{x}\n" for x in self.groups_list])

    def _create_groups_dir(self) -> None:
        for group_id in self.groups_list:
            self._create_group_dir(group_id)

    def _create_group_dir(self, group_id: int) -> None:
        for dir_path in self.required_dirs:
            create_storage_dir(to_path(self.storage_dir, group_id, dir_path))
