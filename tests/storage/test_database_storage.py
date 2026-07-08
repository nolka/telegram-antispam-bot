import pytest
from sqlalchemy import select

from models import Group
from storage import DatabaseStorage


class TestDatabaseStorage:
    """Tests for DatabaseStorage using a real PostgreSQL instance."""

    def test_constructor_initializes_storage(self, db_storage: DatabaseStorage):
        assert db_storage is not None

    def test_is_user_confirmed_false(self, db_storage: DatabaseStorage):
        assert not db_storage.is_user_confirmed(1, 1)

    def test_is_user_confirmed_true(self, db_storage: DatabaseStorage):
        db_storage.set_user_confirmed(1, 1)
        assert db_storage.is_user_confirmed(1, 1)

    def test_set_user_confirmed(self, db_storage: DatabaseStorage):
        assert not db_storage.is_user_confirmed(1, 1)
        db_storage.set_user_confirmed(1, 1)
        assert db_storage.is_user_confirmed(1, 1)

    def test_set_user_confirm_code(self, db_storage: DatabaseStorage):
        assert db_storage.get_user_confirm_code(1, 1) is None
        db_storage.set_user_confirm_code(1, 1, "❤️")
        assert db_storage.get_user_confirm_code(1, 1) == "❤️"

    def test_get_user_confirm_code(self, db_storage: DatabaseStorage):
        assert db_storage.get_user_confirm_code(1, 1) is None
        db_storage.set_user_confirm_code(1, 1, "❤️")
        assert db_storage.get_user_confirm_code(1, 1) == "❤️"

    def test_on_added_to_group_first_time(self, db_storage: DatabaseStorage):
        db_storage.on_added_to_group(2)

    def test_on_added_to_group_when_another_exists(self, db_storage: DatabaseStorage):
        db_storage.on_added_to_group(1)
        db_storage.on_added_to_group(2)

    def test_get_and_save_spam_messages(self, db_storage: DatabaseStorage):
        assert db_storage.get_spam_messages() == []
        db_storage.save_spam_messages(["spam1", "spam2"])
        assert db_storage.get_spam_messages() == ["spam1", "spam2"]

    def test_get_and_save_normal_messages(self, db_storage: DatabaseStorage):
        assert db_storage.get_normal_messages() == []
        db_storage.save_normal_messages(["normal1", "normal2"])
        assert db_storage.get_normal_messages() == ["normal1", "normal2"]

    def test_set_user_confirmed_removes_confirm_code(self, db_storage: DatabaseStorage):
        db_storage.set_user_confirm_code(1, 1, "❤️")
        db_storage.set_user_confirmed(1, 1)
        assert db_storage.get_user_confirm_code(1, 1) is None

    # --- get_user_message_count tests ---

    def test_get_user_message_count_no_messages(self, db_storage: DatabaseStorage):
        assert db_storage.get_user_message_count(1, 1) == 0

    def test_get_user_message_count_single_message(self, db_storage: DatabaseStorage):
        db_storage.save_message(group_id=1, user_id=1, msg_id=100, msg_type="text", text="hello")
        assert db_storage.get_user_message_count(1, 1) == 1

    def test_get_user_message_count_multiple_messages(self, db_storage: DatabaseStorage):
        for i in range(5):
            db_storage.save_message(
                group_id=1, user_id=1, msg_id=100 + i, msg_type="text", text="msg"
            )
        assert db_storage.get_user_message_count(1, 1) == 5

    def test_get_user_message_count_different_user(self, db_storage: DatabaseStorage):
        db_storage.save_message(group_id=1, user_id=1, msg_id=100, msg_type="text", text="user1")
        db_storage.save_message(group_id=1, user_id=2, msg_id=101, msg_type="text", text="user2")
        assert db_storage.get_user_message_count(1, 1) == 1
        assert db_storage.get_user_message_count(1, 2) == 1

    def test_get_user_message_count_different_group(self, db_storage: DatabaseStorage):
        db_storage.save_message(group_id=1, user_id=1, msg_id=100, msg_type="text", text="g1")
        db_storage.save_message(group_id=2, user_id=1, msg_id=101, msg_type="text", text="g2")
        assert db_storage.get_user_message_count(1, 1) == 1
        assert db_storage.get_user_message_count(2, 1) == 1

    # --- session lifecycle tests ---

    def test_session_is_obtained_and_usable(self, db_storage: DatabaseStorage):
        """_get_session yields a real, working SQLAlchemy session."""
        with db_storage._get_session() as session:
            # session — это реальный объект SQLAlchemy, с которым можно работать
            result = session.execute(select(Group)).all()
            assert isinstance(result, list)

    def test_session_stays_usable_after_exception(self, db_storage: DatabaseStorage):
        """Сессия не утекает: после исключения внутри _get_session
        следующий запрос всё ещё работает."""
        # Вызываем исключение внутри контекста сессии
        with pytest.raises(ValueError, match="boom"):
            with db_storage._get_session() as s:
                # убеждаемся что сессия живая
                s.execute(select(Group))
                raise ValueError("boom")

        # Если бы сессия утекла, пул соединений исчерпался бы
        # и следующий запрос упал бы с ошибками подключения.
        # Запускаем несколько итераций, чтобы накопить потенциальную утечку.
        for _ in range(10):
            with pytest.raises(ValueError):
                with db_storage._get_session() as s:
                    s.execute(select(Group))
                    raise ValueError("boom")

        # Финальный запрос: если сессии не утекли — он отработает.
        with db_storage._get_session() as s:
            s.execute(select(Group))
