"""
Integration tests for AntispamVerification plugin.

Verifies the full flow:
- New user joins → verification message sent with inline buttons
- Already confirmed user → no message sent
- Bot joins group → group registered, no verification message
- User selects correct emoji → confirmed, message deleted, timer cancelled
- User selects wrong emoji → logged as incorrect, not confirmed
- Inactive user → kicked after timeout, message deleted
"""

import unittest
from unittest.mock import MagicMock, Mock, call, patch

from plugins.members import AntispamVerification


class TestAntispamVerification(unittest.TestCase):
    """Tests for AntispamVerification plugin."""

    def _make_plugin(self, kick_after_sec=180):
        """Helper to create a plugin with mocked dependencies."""
        engine_mock = Mock()
        engine_mock.storage = Mock()
        engine_mock.metrics = Mock()
        logger_mock = Mock()
        plugin = AntispamVerification(logger_mock, engine_mock, kick_after_sec)
        return plugin, engine_mock, logger_mock

    def _make_join_message(self, chat_id=-100, user_id=123, username="newuser"):
        """Helper to create a mock message simulating a new user joining."""
        message = Mock()
        message.chat = Mock()
        message.chat.id = chat_id
        message.chat.title = "Test Group"
        message.new_chat_members = [Mock(id=user_id, username=username, full_name="New User")]
        return message

    # ── Execute: new user joins ──────────────────────────────────────────────

    @patch("plugins.members.Timer")
    def test_new_user_receives_verification_message(self, timer_mock):
        """When a new user joins, a verification message is sent with inline buttons."""
        plugin, engine, _ = self._make_plugin()

        engine.storage.is_user_confirmed.return_value = False
        engine.storage.get_user_confirm_code.return_value = None

        mock_response = Mock()
        mock_response.get.return_value.id = 999
        engine.send_message.return_value = Mock(get=Mock(return_value=mock_response))

        message = self._make_join_message()
        plugin.execute(engine, message)

        # Verify message was sent
        engine.send_message.assert_called_once()
        call_kwargs = engine.send_message.call_args.kwargs
        self.assertEqual(call_kwargs["chat_id"], -100)
        self.assertEqual(call_kwargs["parse_mode"], "markdownV2")
        self.assertIsNotNone(call_kwargs["reply_markup"])  # inline keyboard present
        self.assertIn("New User", call_kwargs["text"])

        # Verify confirm code was saved with a valid emoji
        engine.storage.set_user_confirm_code.assert_called_once()
        saved_code = engine.storage.set_user_confirm_code.call_args.args[2]
        assert saved_code in plugin.emojies

        # Verify timer was started
        timer_mock.assert_called_once()
        timer_mock.return_value.start.assert_called_once()

    @patch("plugins.members.Timer")
    def test_timer_kicks_inactive_user(self, timer_mock):
        """A Timer is created with kick_inactive callback."""
        plugin, engine, _ = self._make_plugin(kick_after_sec=60)

        engine.storage.is_user_confirmed.return_value = False
        engine.storage.get_user_confirm_code.return_value = None
        engine.send_message.return_value = Mock(get=Mock(return_value=Mock(id=999)))

        message = self._make_join_message()
        plugin.execute(engine, message)

        # Verify timer args include kick_inactive
        call_args = timer_mock.call_args
        self.assertEqual(call_args.args[0], 60)  # delay
        self.assertEqual(call_args.args[1], plugin.kick_inactive)  # callback
        # Callback args are passed as keyword argument `args`
        timer_args = call_args.kwargs["args"]
        self.assertEqual(timer_args, (engine, -100, 123, 999))

    # ── Execute: already confirmed user ──────────────────────────────────────

    def test_confirmed_user_skips_verification(self):
        """Already confirmed users don't receive a verification message."""
        plugin, engine, _ = self._make_plugin()
        engine.storage.is_user_confirmed.return_value = True

        message = self._make_join_message()
        plugin.execute(engine, message)

        engine.send_message.assert_not_called()

    # ── Execute: bot joins group ─────────────────────────────────────────────

    def test_bot_joining_registers_group(self):
        """When the bot itself joins a group, it registers the group but doesn't send verification."""
        plugin, engine, _ = self._make_plugin()
        engine.bot_username = "mybot"

        message = self._make_join_message(username="mybot")
        plugin.execute(engine, message)

        engine.on_bot_added_to_group.assert_called_once_with(-100)
        engine.send_message.assert_not_called()

    # ── Callback: user selects correct emoji ─────────────────────────────────

    def test_correct_emoji_confirms_user(self):
        """When user selects the correct emoji, they are confirmed."""
        plugin, engine, _ = self._make_plugin()
        engine.storage.is_user_confirmed.return_value = False
        engine.storage.get_user_confirm_code.return_value = "❤️"

        callback = Mock()
        callback.message.chat.id = -100
        callback.from_user.id = 123
        callback.from_user.full_name = "New User"
        callback.data = "verify_❤️"

        plugin._user_selected_answer(callback)

        engine.storage.set_user_confirmed.assert_called_once_with(-100, 123)
        engine.delete_message.assert_called_once_with(chat_id=-100, message_id=callback.message.id)
        engine.metrics.inc_captha_solved_total.assert_called_once_with("❤️")

    # ── Callback: user selects wrong emoji ───────────────────────────────────

    def test_wrong_emoji_does_not_confirm_user(self):
        """When user selects wrong emoji, they are NOT confirmed."""
        plugin, engine, logger = self._make_plugin()
        engine.storage.is_user_confirmed.return_value = False
        engine.storage.get_user_confirm_code.return_value = "❤️"

        callback = Mock()
        callback.message.chat.id = -100
        callback.from_user.id = 123
        callback.from_user.full_name = "New User"
        callback.data = "verify_🙈"  # wrong emoji

        plugin._user_selected_answer(callback)

        engine.storage.set_user_confirmed.assert_not_called()
        engine.delete_message.assert_not_called()
        # Verify that the wrong answer was logged
        logger.info.assert_called()

    # ── Callback: ignored non-verify callbacks ───────────────────────────────

    def test_non_verify_callback_is_ignored(self):
        """Callbacks with data not starting with 'verify_' are ignored."""
        plugin, engine, _ = self._make_plugin()

        callback = Mock()
        callback.data = "something_else"

        plugin._user_selected_answer(callback)

        engine.storage.set_user_confirmed.assert_not_called()

    # ── kick_inactive ────────────────────────────────────────────────────────

    def test_kick_inactive_kicks_unconfirmed_user(self):
        """kick_inactive kicks unconfirmed users and deletes the captcha message."""
        plugin, engine, _ = self._make_plugin()
        engine.storage.is_user_confirmed.return_value = False

        plugin.kick_inactive(engine, -100, 123, 999)

        engine.kick_chat_member.assert_called_once_with(-100, 123)
        engine.delete_message.assert_called_once_with(-100, 999)

    def test_kick_inactive_skips_confirmed_user(self):
        """kick_inactive does nothing if the user is already confirmed."""
        plugin, engine, _ = self._make_plugin()
        engine.storage.is_user_confirmed.return_value = True

        plugin.kick_inactive(engine, -100, 123, 999)

        engine.kick_chat_member.assert_not_called()
        engine.delete_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
