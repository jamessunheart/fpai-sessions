"""Local Telegram voice pipeline for Sunheart Brain.

The live bot receives complete Telegram voice notes, not a realtime socket, so
this module keeps the Pipecat adoption boundary explicit while preserving the
existing long-polling transport. The stage order is:

    Telegram voice bytes -> faster-whisper STT -> existing chat/LLM path
    -> Kokoro TTS -> Telegram voice bytes

Pipecat is treated as an installed runtime dependency and readiness signal for
the future streaming transport. The synchronous model calls are isolated here
so tgbot.py can stay focused on routing, auth, and message handling.
"""
from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger("curator.voice_pipeline")


@dataclass(frozen=True)
class VoiceDependencyStatus:
    pipecat: bool
    faster_whisper: bool
    kokoro: bool
    ffmpeg: bool
    soundfile: bool
    numpy: bool

    @property
    def stt_ready(self) -> bool:
        return self.faster_whisper

    @property
    def tts_ready(self) -> bool:
        return self.kokoro and self.ffmpeg and (self.soundfile or self.numpy)

    @property
    def local_ready(self) -> bool:
        return self.pipecat and self.stt_ready and self.tts_ready

    def missing(self) -> list[str]:
        missing: list[str] = []
        if not self.pipecat:
            missing.append("pipecat")
        if not self.faster_whisper:
            missing.append("faster-whisper")
        if not self.kokoro:
            missing.append("kokoro")
        if not self.ffmpeg:
            missing.append("ffmpeg")
        if not (self.soundfile or self.numpy):
            missing.append("soundfile-or-numpy")
        return missing


def dependency_status(
    *,
    finder: Callable[[str], object | None] = importlib.util.find_spec,
    ffmpeg_path: str | None = None,
) -> VoiceDependencyStatus:
    """Return install readiness without importing heavyweight model packages."""
    ffmpeg = Path(ffmpeg_path or os.environ.get("SH_TGBOT_FFMPEG", "ffmpeg"))
    return VoiceDependencyStatus(
        pipecat=bool(finder("pipecat")),
        faster_whisper=bool(finder("faster_whisper")),
        kokoro=bool(finder("kokoro")),
        ffmpeg=_ffmpeg_available(ffmpeg),
        soundfile=bool(finder("soundfile")),
        numpy=bool(finder("numpy")),
    )


def local_voice_enabled() -> bool:
    return os.environ.get("SH_TGBOT_VOICE_PROVIDER", "local").strip().lower() in {
        "local",
        "pipecat",
        "sovereign",
    }


def local_voice_strict() -> bool:
    return os.environ.get("SH_TGBOT_VOICE_LOCAL_STRICT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def transcribe(audio_bytes: bytes, *, suffix: str = ".ogg") -> str | None:
    """Transcribe Telegram audio with faster-whisper in a worker thread."""
    if not audio_bytes:
        return None
    return await asyncio.to_thread(_transcribe_sync, audio_bytes, suffix)


async def synthesize(text: str) -> tuple[bytes, str, str] | None:
    """Synthesize speech with Kokoro and transcode to OGG Opus for Telegram."""
    if not text or not text.strip():
        return None
    return await asyncio.to_thread(_synthesize_sync, text.strip())


def _transcribe_sync(audio_bytes: bytes, suffix: str) -> str | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        log.warning("local voice STT unavailable: %s", e)
        return None

    model_name = os.environ.get("SH_LOCAL_STT_MODEL", "base")
    device = os.environ.get("SH_LOCAL_STT_DEVICE", "cpu")
    compute_type = os.environ.get("SH_LOCAL_STT_COMPUTE_TYPE", "int8")
    beam_size = int(os.environ.get("SH_LOCAL_STT_BEAM_SIZE", "1"))
    language = os.environ.get("SH_LOCAL_STT_LANGUAGE") or None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            source = f.name
        try:
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            segments, _info = model.transcribe(
                source,
                beam_size=beam_size,
                vad_filter=True,
                language=language,
            )
            text = " ".join((seg.text or "").strip() for seg in segments).strip()
            return text or None
        finally:
            Path(source).unlink(missing_ok=True)
    except Exception as e:
        log.exception("local voice STT failed: %s", e)
        return None


def _synthesize_sync(text: str) -> tuple[bytes, str, str] | None:
    try:
        from kokoro import KPipeline  # type: ignore
    except Exception as e:
        log.warning("local voice TTS unavailable: %s", e)
        return None

    voice = os.environ.get("SH_LOCAL_TTS_VOICE", "af_heart")
    lang_code = os.environ.get("SH_LOCAL_TTS_LANG", "a")
    speed = float(os.environ.get("SH_LOCAL_TTS_SPEED", "1.0"))
    sample_rate = int(os.environ.get("SH_LOCAL_TTS_SAMPLE_RATE", "24000"))
    ffmpeg = Path(os.environ.get("SH_TGBOT_FFMPEG", "ffmpeg"))

    try:
        pipeline = KPipeline(lang_code=lang_code)
        chunks = pipeline(text, voice=voice, speed=speed)
        audio = _collect_kokoro_audio(chunks)
        if audio is None:
            return None
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "reply.wav"
            ogg_path = Path(td) / "reply.ogg"
            _write_wav(wav_path, audio, sample_rate=sample_rate)
            cmd = [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(wav_path),
                "-c:a",
                "libopus",
                "-b:a",
                os.environ.get("SH_LOCAL_TTS_OPUS_BITRATE", "32k"),
                str(ogg_path),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return ogg_path.read_bytes(), "audio/ogg", "ogg"
    except Exception as e:
        log.exception("local voice TTS failed: %s", e)
        return None


def _collect_kokoro_audio(chunks: Iterable[object]) -> object | None:
    parts: list[object] = []
    for item in chunks:
        if isinstance(item, tuple) and item:
            parts.append(item[-1])
        else:
            parts.append(item)
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    try:
        import numpy as np  # type: ignore

        return np.concatenate(parts)
    except Exception as e:
        log.warning("could not concatenate Kokoro audio chunks: %s", e)
        return parts[0]


def _write_wav(path: Path, audio: object, *, sample_rate: int) -> None:
    try:
        import soundfile as sf  # type: ignore

        sf.write(str(path), audio, sample_rate)
        return
    except Exception:
        pass

    try:
        import numpy as np  # type: ignore

        arr = np.asarray(audio)
        if arr.dtype.kind == "f":
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767).astype("<i2")
        else:
            arr = arr.astype("<i2")
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1 if arr.ndim == 1 else arr.shape[1])
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(arr.tobytes())
        return
    except Exception as e:
        raise RuntimeError(f"could not write wav: {e}") from e


def _ffmpeg_available(ffmpeg: Path) -> bool:
    try:
        subprocess.run(
            [str(ffmpeg), "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return True
    except Exception:
        return False
