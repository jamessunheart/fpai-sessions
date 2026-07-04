from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("voice_pipeline.py")
SPEC = importlib.util.spec_from_file_location("voice_pipeline", MODULE_PATH)
assert SPEC and SPEC.loader
voice_pipeline = importlib.util.module_from_spec(SPEC)
sys.modules["voice_pipeline"] = voice_pipeline
SPEC.loader.exec_module(voice_pipeline)


class VoicePipelineTest(unittest.TestCase):
    def test_dependency_status_reports_ready_and_missing(self) -> None:
        present = {"pipecat", "faster_whisper", "kokoro", "soundfile", "numpy"}

        def finder(name: str) -> object | None:
            return object() if name in present else None

        ready = voice_pipeline.dependency_status(finder=finder, ffmpeg_path="/bin/true")
        self.assertTrue(ready.local_ready)
        self.assertEqual(ready.missing(), [])

        with patch.dict(os.environ, {}, clear=True):
            missing = voice_pipeline.dependency_status(finder=lambda _name: None, ffmpeg_path="/bin/false")
        self.assertFalse(missing.local_ready)
        self.assertIn("pipecat", missing.missing())
        self.assertIn("faster-whisper-or-openai-whisper", missing.missing())
        self.assertIn("kokoro", missing.missing())

    def test_openai_whisper_key_is_stt_fallback_when_faster_whisper_absent(self) -> None:
        present = {"pipecat", "kokoro", "soundfile", "numpy"}

        def finder(name: str) -> object | None:
            return object() if name in present else None

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            status = voice_pipeline.dependency_status(finder=finder, ffmpeg_path="/bin/true")

        self.assertFalse(status.faster_whisper)
        self.assertTrue(status.openai_whisper)
        self.assertTrue(status.stt_ready)
        self.assertNotIn("faster-whisper-or-openai-whisper", status.missing())

    def test_provider_env_controls_local_and_strict_modes(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(voice_pipeline.local_voice_enabled())
            self.assertFalse(voice_pipeline.local_voice_strict())
        with patch.dict(os.environ, {"SH_TGBOT_VOICE_PROVIDER": "openai"}, clear=True):
            self.assertFalse(voice_pipeline.local_voice_enabled())
        with patch.dict(os.environ, {"SH_TGBOT_VOICE_LOCAL_STRICT": "1"}, clear=True):
            self.assertTrue(voice_pipeline.local_voice_strict())

    def test_collect_kokoro_audio_accepts_tuple_chunks(self) -> None:
        chunks = [
            ("graphemes", "phonemes", [0.1, 0.2]),
        ]
        self.assertEqual(voice_pipeline._collect_kokoro_audio(chunks), [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
