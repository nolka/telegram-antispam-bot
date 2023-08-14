import os
from abc import ABC, abstractmethod
from codecs import open


class AbstractStorage(ABC):
    @abstractmethod
    def is_user_confirmed(self, group_id: int,  user_id: int) -> bool:
        pass

    @abstractmethod
    def set_user_confirmed(self, group_id: int,  user_id: int) -> bool:
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


def _prepare_path(path: str) -> str:
    return os.path.join(*os.path.split(path))


def _path(*args) -> str:
    return os.path.join(*args)


def _create_storage_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


class FileSystem(AbstractStorage):
    confirmed_dir = "confirmed"
    confirm_codes_dir = "confirm_codes"

    groups_list_file = "groups.txt"

    required_dirs = (confirmed_dir, confirm_codes_dir)

    def __init__(self, path: str):
        self.storage_dir = _prepare_path(path)
        self.groups_list = set()

        if os.path.exists(_path(self.storage_dir, self.groups_list_file)):
            with open(_path(self.storage_dir, self.groups_list_file), "r") as f:
                self.groups_list = [int(x) for x in f.readlines()]

        if not os.path.exists(self.storage_dir):
            _create_storage_dir(self.storage_dir)

        self._create_groups_dir()

    def is_user_confirmed(self, group_id: int, user_id: int) -> bool:
        return os.path.exists(_path(self.storage_dir, str(group_id), "confirmed", str(user_id)))
    
    def set_user_confirmed(self, group_id: int, user_id: int) -> bool:
        confirmed_file = _path(self.storage_dir, str(group_id), "confirmed", str(user_id))
        confirm_code_file = _path(self.storage_dir, str(group_id), "confirm_codes", str(user_id))
        with open(confirmed_file, "w") as f:
            os.unlink(confirm_code_file)

    def set_user_confirm_code(self, group_id: int, user_id: int, confirm_code: str) -> None:
        with open(_path(self.storage_dir, str(group_id), "confirm_codes", str(user_id)), "w", encoding="utf-8") as f:
            f.write(confirm_code)

    def get_user_confirm_code(self, group_id: int, user_id: int) -> str | None:
        try:
            with open(_path(self.storage_dir, str(group_id), "confirm_codes", str(user_id)), "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return None
        
    def on_added_to_group(self, group_id: int) -> None:
        self._create_group_dir(group_id)
        self.groups_list.add(group_id)

        self._save_groups_list()

    def _save_groups_list(self) -> None:
        with open(_path(self.storage_dir, self.groups_list_file), "w") as f:
            f.writelines([f"{x}\n" for x in self.groups_list])

    def _create_groups_dir(self) -> None:
        for group_id in self.groups_list:
            self._create_group_dir(group_id)

    def _create_group_dir(self, group_id: int) -> None:
        for dir in self.required_dirs:
            _create_storage_dir(_path(self.storage_dir, str(group_id), dir))
