"""Speech-to-text (voice dictation) module.

In production this should call an OpenAI audio transcription model (e.g. Whisper-based).
"""
from typing import Dict, Any


def transcribe_audio(audio_bytes: bytes, language: str = "es") -> Dict[str, Any]:
    # Placeholder STT implementation.
    return {"text": "[STT placeholder] Audio transcription is not configured in this environment."}
