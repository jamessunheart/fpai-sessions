from __future__ import annotations

import unittest
from unittest import mock

from . import tgbot


class TelegramConstitutionCommandTest(unittest.IsolatedAsyncioTestCase):
    async def test_constitution_command_sends_all_rendered_messages(self) -> None:
        helper = mock.Mock()
        helper.surface_to_telegram.return_value = ["part one", "part two"]

        with mock.patch.object(tgbot, "_load_constitution_surface", return_value=helper), \
                mock.patch.object(tgbot.tg, "send", new=mock.AsyncMock(return_value=True)) as send:
            reply = await tgbot._handle_command("/constitution", 123)

        self.assertIsNone(reply)
        helper.surface_to_telegram.assert_called_once_with(send=False)
        self.assertEqual(send.await_count, 2)
        send.assert_any_await("part one")
        send.assert_any_await("part two")

    async def test_constitution_command_reports_loader_failure(self) -> None:
        with mock.patch.object(tgbot, "_load_constitution_surface", side_effect=RuntimeError("missing")):
            reply = await tgbot._handle_command("/constitution", 123)

        self.assertIn("constitution surface failed", reply or "")
        self.assertIn("missing", reply or "")


if __name__ == "__main__":
    unittest.main()

