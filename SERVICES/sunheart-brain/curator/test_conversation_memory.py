from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("conversation_memory.py")


class FakeLLMResult:
    text = "James prefers morning build summaries.\nDecision: keep repo canonical."


async def fake_complete(*args, **kwargs):
    return FakeLLMResult()


async def fake_embed_query(text: str):
    return [0.1, 0.2, 0.3]


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, sql: str, params: tuple) -> None:
        self.calls.append((sql, params))


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def cursor(self) -> FakeCursor:
        return self._cursor


class ConversationMemoryTest(unittest.TestCase):
    def load_module(self, cursor: FakeCursor):
        package = types.ModuleType("curator")
        package.__path__ = [str(MODULE_PATH.parent)]
        sys.modules["curator"] = package
        sys.modules["curator.llm"] = types.SimpleNamespace(complete=fake_complete)
        sys.modules["curator.tgbot"] = types.SimpleNamespace(_embed_query=fake_embed_query)
        sys.modules["curator.db"] = types.SimpleNamespace(connect=lambda: FakeConnection(cursor))
        spec = importlib.util.spec_from_file_location("curator.conversation_memory", MODULE_PATH)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["curator.conversation_memory"] = module
        spec.loader.exec_module(module)
        return module

    def test_compress_and_store_writes_tg_memory_chunk(self) -> None:
        cursor = FakeCursor()
        module = self.load_module(cursor)

        memory = asyncio.run(
            module.compress_and_store(
                "chat-1",
                [("user", "I prefer morning summaries."), ("bot", "Noted.")],
            )
        )

        self.assertIn("morning build summaries", memory)
        self.assertEqual(len(cursor.calls), 1)
        sql, params = cursor.calls[0]
        self.assertIn("brain_index.note_chunks", sql)
        self.assertTrue(params[0].startswith("tgmem-chat-1-"))
        self.assertEqual(params[1], memory)
        self.assertEqual(params[3], [0.1, 0.2, 0.3])
        self.assertEqual(params[5], module.MEMORY_SOURCE)

    def test_empty_turns_are_noop(self) -> None:
        cursor = FakeCursor()
        module = self.load_module(cursor)

        self.assertIsNone(asyncio.run(module.compress_and_store("chat-1", [])))
        self.assertEqual(cursor.calls, [])


if __name__ == "__main__":
    unittest.main()
