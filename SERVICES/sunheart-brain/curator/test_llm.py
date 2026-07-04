from __future__ import annotations

import unittest
from unittest import mock

from . import llm


class _FakeClaudeProcess:
    def __init__(self, *, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


class ClaudeCliProviderTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._provider = llm.PROVIDER

    def tearDown(self) -> None:
        llm.PROVIDER = self._provider

    async def test_complete_uses_claude_cli_provider(self) -> None:
        llm.PROVIDER = "claude-cli"
        proc = _FakeClaudeProcess(stdout=b'{"ok": true}\n')

        with mock.patch.dict(llm.os.environ, {"ANTHROPIC_API_KEY": "metered-key", "CLAUDE_CODE_OAUTH_TOKEN": "oauth"}, clear=False), \
                mock.patch.object(llm.shutil, "which", return_value="/usr/bin/claude"), \
                mock.patch.object(llm.asyncio, "create_subprocess_exec", new=mock.AsyncMock(return_value=proc)) as run:
            result = await llm.complete("system prompt", "user prompt", max_tokens=777)

        self.assertEqual(result.text, '{"ok": true}')
        self.assertEqual(result.model, "claude-cli:claude -p")
        run.assert_awaited_once()
        args = run.await_args.args
        self.assertEqual(args[:2], ("claude", "-p"))
        self.assertIn("system prompt\n\nuser prompt", args[2])
        self.assertIn("Return ONLY a single JSON object", args[2])
        env = run.await_args.kwargs["env"]
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual("oauth", env["CLAUDE_CODE_OAUTH_TOKEN"])

    async def test_claude_cli_missing_falls_back_to_ollama(self) -> None:
        fallback = llm.LLMResult("local", "ollama:test", "hash", 1, 2)

        with mock.patch.object(llm.shutil, "which", return_value=None), \
                mock.patch.object(llm, "_ollama", new=mock.AsyncMock(return_value=fallback)) as ollama:
            result = await llm._claude_cli("system", "user", 333, 0.7, "hash")

        self.assertEqual(result.text, fallback.text)
        self.assertEqual(result.model, fallback.model)
        ollama.assert_awaited_once_with("system", "user", 333, 0.7, "hash")
        self.assertEqual(result.fallback_from, "claude-cli")
        self.assertIn("not found", result.fallback_reason)

    async def test_claude_cli_nonzero_exit_falls_back_to_ollama(self) -> None:
        proc = _FakeClaudeProcess(returncode=1, stderr=b"not logged in")
        fallback = llm.LLMResult("local", "ollama:test", "hash", 1, 2)

        with mock.patch.object(llm.shutil, "which", return_value="/usr/bin/claude"), \
                mock.patch.object(llm.asyncio, "create_subprocess_exec", new=mock.AsyncMock(return_value=proc)), \
                mock.patch.object(llm, "_ollama", new=mock.AsyncMock(return_value=fallback)) as ollama:
            result = await llm._claude_cli("system", "user", 444, 0.4, "hash")

        self.assertEqual(result.text, fallback.text)
        self.assertEqual(result.model, fallback.model)
        ollama.assert_awaited_once_with("system", "user", 444, 0.4, "hash")
        self.assertEqual(result.fallback_from, "claude-cli")
        self.assertIn("not logged in", result.fallback_reason)

    async def test_claude_cli_self_test_reports_nonzero_reason(self) -> None:
        proc = _FakeClaudeProcess(returncode=1, stderr=b"not logged in")

        with mock.patch.object(llm.shutil, "which", return_value="/usr/bin/claude"), \
                mock.patch.object(llm.asyncio, "create_subprocess_exec", new=mock.AsyncMock(return_value=proc)):
            ok, reason = await llm.claude_cli_self_test()

        self.assertFalse(ok)
        self.assertIn("not logged in", reason)


if __name__ == "__main__":
    unittest.main()
