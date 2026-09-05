from __future__ import annotations

import unittest
from unittest import mock

from . import tgbot


class TelegramConstitutionCommandTest(unittest.IsolatedAsyncioTestCase):
    async def test_north_command_uses_read_only_attention_renderer(self) -> None:
        helper = mock.Mock()
        snapshot = {"authority": "lens_only", "actuation": False}
        helper.load_snapshot.return_value = snapshot
        helper.render_snapshot.return_value = "<b>North</b>\nOne genuine decision"

        with mock.patch.object(tgbot, "_load_north_attention_tgbot", return_value=helper):
            reply = await tgbot._handle_command("/north", 123)

        self.assertEqual(reply, "<b>North</b>\nOne genuine decision")
        helper.load_snapshot.assert_called_once_with(tgbot._repo_root())
        helper.render_snapshot.assert_called_once_with(snapshot, escape=tgbot.tg._esc)

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

    async def test_builds_command_returns_queue_snapshot(self) -> None:
        helper = mock.Mock()
        helper.render_queue_snapshot.return_value = "<b>Builds</b>\npending: <b>1</b>"

        with mock.patch.object(tgbot, "_load_build_alerts", return_value=helper):
            reply = await tgbot._handle_command("/builds", 123)

        self.assertEqual(reply, "<b>Builds</b>\npending: <b>1</b>")
        helper.render_queue_snapshot.assert_called_once()


if __name__ == "__main__":
    unittest.main()
