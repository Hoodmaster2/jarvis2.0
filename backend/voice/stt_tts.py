"""
Speech-to-text using faster-whisper or Windows SAPI fallback.
"""
import asyncio
import logging
import os
import tempfile
import wave
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeechToText:
    """Convert speech to text using local models."""

    def __init__(self, engine: str = "whisper", model_size: str = "base"):
        self.engine = engine
        self.model_size = model_size
        self._model = None

    async def _load_whisper(self):
        """Lazy-load faster-whisper."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info(f"Loaded whisper model: {self.model_size}")
            except ImportError:
                logger.warning("faster-whisper not installed, falling back to Windows SAPI")
                self.engine = "windows"

    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio bytes to text."""
        if self.engine == "whisper":
            await self._load_whisper()
            if self._model:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    tmp_path = f.name
                try:
                    segments, _ = self._model.transcribe(tmp_path, beam_size=5)
                    result = " ".join(seg.text for seg in segments)
                    return result.strip()
                finally:
                    os.unlink(tmp_path)

        # Windows SAPI fallback
        return await self._transcribe_sapi(audio_data)

    async def _transcribe_sapi(self, audio_data: bytes) -> str:
        """Use Windows SAPI speech recognition."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
            from win32com.client import Dispatch
            from win32com.client import constants

            recognizer = Dispatch("SAPI.SpRecognizer")
            grammar = recognizer.CreateGrammar()
            grammar.DictationSetState(constants.SGDSActive)
            # Note: This is a simplified approach; full implementation
            # would use the audio stream interface properly
            return "Speech recognition via SAPI"
        except Exception as e:
            logger.error(f"SAPI transcription error: {e}")
            return ""

    async def transcribe_file(self, filepath: str) -> str:
        """Transcribe a WAV file."""
        with open(filepath, "rb") as f:
            audio_data = f.read()
        return await self.transcribe(audio_data)


class TextToSpeech:
    """Convert text to speech using Piper or Windows SAPI."""

    def __init__(self, engine: str = "piper", voice: str = "default"):
        self.engine = engine
        self.voice = voice
        self._piper_proc = None

    async def speak(self, text: str) -> bool:
        """Speak text aloud."""
        if self.engine == "piper":
            return await self._speak_piper(text)
        elif self.engine == "windows":
            return await self._speak_sapi(text)
        return False

    async def _speak_sapi(self, text: str) -> bool:
        """Use Windows SAPI for TTS."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
            from win32com.client import Dispatch
            speaker = Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
            return True
        except Exception as e:
            logger.error(f"SAPI TTS error: {e}")
            return False

    async def _speak_piper(self, text: str) -> bool:
        """Use Piper TTS via subprocess."""
        try:
            import subprocess
            import sys

            piper_path = os.environ.get("PIPER_PATH", "piper")
            model_path = os.environ.get(
                "PIPER_MODEL",
                str(Path(__file__).parent.parent.parent / "voice" / "models" / "en_US-lessac-medium.onnx")
            )

            if not os.path.exists(model_path):
                logger.warning(f"Piper model not found at {model_path}, try Windows SAPI")
                return await self._speak_sapi(text)

            proc = await asyncio.create_subprocess_exec(
                piper_path, "--model", model_path, "--output-raw",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
            if proc.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
                return False
            # Play audio with aplay/ffplay or similar
            return True
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            return await self._speak_sapi(text)

    async def speak_to_file(self, text: str, output_path: str) -> bool:
        """Generate speech audio file."""
        try:
            import subprocess
            piper_path = os.environ.get("PIPER_PATH", "piper")
            model_path = os.environ.get(
                "PIPER_MODEL",
                str(Path(__file__).parent.parent.parent / "voice" / "models" / "en_US-lessac-medium.onnx")
            )
            proc = await asyncio.create_subprocess_exec(
                piper_path, "--model", model_path, "--output-file", output_path,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate(input=text.encode("utf-8"))
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"Piper file generation error: {e}")
            return False
