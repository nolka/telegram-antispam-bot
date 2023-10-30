import unittest
from unittest.mock import Mock, patch
from plugins.members import CASBan


class TestCASBan(unittest.TestCase):
    @patch(
        "requests.get",
        return_value=Mock(status_code=200, **{"json.return_value": {"ok": True}}),
    )
    def test_check_cas_ban_user_banned(self, requests_mock):
        plugin = CASBan(Mock())
        engine_mock = Mock()
        message_mock = Mock(new_chat_members=[Mock(id=123)])

        plugin.execute(engine_mock, message_mock)

        requests_mock.assert_called_once()
        engine_mock.ban_user.assert_called()

    @patch(
        "requests.get",
        return_value=Mock(status_code=200, **{"json.return_value": {"ok": False}}),
    )
    def test_check_cas_ban_user_not_banned(self, requests_mock):
        plugin = CASBan(Mock())
        engine_mock = Mock()
        message_mock = Mock(new_chat_members=[Mock(id=123)])

        plugin.execute(engine_mock, message_mock)

        requests_mock.assert_called_once()
        engine_mock.ban_user.assert_not_called()


class TestAntispamVerification(unittest.TestCase):
    # TODO: Implement
    pass