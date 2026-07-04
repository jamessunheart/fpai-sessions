import sys
import types
import unittest
from unittest import mock

from tools.council import self_diagnostic


class SelfDiagnosticImportGuardTests(unittest.TestCase):
    def test_ask_bot_directly_loads_tgbot_by_file_location(self):
        loaded = types.SimpleNamespace()

        async def search(question, k):
            return [{"text": f"{question}:{k}"}]

        async def synthesize(question, hits):
            return f"answer:{question}:{hits[0]['text']}"

        class Loader:
            @staticmethod
            def exec_module(module):
                module._search_brain = search
                module._synthesize_answer = synthesize

        spec = types.SimpleNamespace(loader=Loader())
        before = list(sys.path)
        with mock.patch("importlib.util.spec_from_file_location", return_value=spec) as spec_from_file:
            with mock.patch("importlib.util.module_from_spec", return_value=loaded):
                answer = self_diagnostic._ask_bot_directly("gap?")

        self.assertEqual(answer, "answer:gap?:gap?:5")
        spec_from_file.assert_called_once_with("sh_brain_tgbot", "/opt/sh-brain-src/curator/tgbot.py")
        self.assertEqual(sys.path, before)


if __name__ == "__main__":
    unittest.main()
