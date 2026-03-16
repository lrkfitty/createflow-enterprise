"""
transcribe_voice.py
--------------------
Voice Dictation — converts audio bytes to text using OpenAI Whisper API.

Layer 3 (Execution) script. Called by the Art Director tab's mic button in app.py.

Input:  audio_bytes (bytes) — raw audio from st.audio_input (WAV/WebM/MP4/OGG)
Output: str — transcribed text, or empty string on failure
"""

import os
import io
import tempfile
from dotenv import load_dotenv

load_dotenv()


def transcribe_voice(audio_bytes: bytes, language: str = None) -> str:
    """
    Transcribe audio bytes to text using OpenAI Whisper API.

    Args:
        audio_bytes:  Raw audio bytes from Streamlit's st.audio_input().
                      Supports WAV, MP3, MP4, MPEG, MPGA, M4A, OGG, OGA, WEBM.
        language:     Optional ISO-639-1 language code (e.g. "en") to improve accuracy.
                      If None, Whisper auto-detects the language.

    Returns:
        Transcribed text string. Returns "" on failure.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[transcribe_voice] ERROR: OPENAI_API_KEY not found in .env")
        return ""

    if not audio_bytes or len(audio_bytes) == 0:
        print("[transcribe_voice] ERROR: Empty audio bytes received.")
        return ""

    # Whisper requires a file-like object with a name attribute for format detection.
    # Write to a named temp file so the extension is preserved.
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(audio_bytes)

        client = OpenAI(api_key=api_key)

        with open(tmp_path, "rb") as audio_file:
            kwargs = {
                "model": "whisper-1",
                "file": audio_file,
                "response_format": "text",
            }
            if language:
                kwargs["language"] = language

            transcript = client.audio.transcriptions.create(**kwargs)

        # Clean up temp file
        os.unlink(tmp_path)

        # response_format="text" returns a plain string
        result = str(transcript).strip()
        print(f"[transcribe_voice] ✅ Transcribed: '{result[:80]}...' " if len(result) > 80 else f"[transcribe_voice] ✅ '{result}'")
        return result

    except Exception as e:
        print(f"[transcribe_voice] Whisper API error: {e}")
        # Clean up temp file on error
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return ""


def transcribe_voice_file(file_path: str, language: str = None) -> str:
    """
    Convenience wrapper: transcribe from a local audio file path.

    Args:
        file_path:  Absolute path to an audio file.
        language:   Optional language code.

    Returns:
        Transcribed text string.
    """
    if not os.path.exists(file_path):
        print(f"[transcribe_voice] File not found: {file_path}")
        return ""

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    return transcribe_voice(audio_bytes, language=language)


# ─── Quick Test (run directly) ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        print(f"\n🎙️ Transcribing: {test_path}")
        result = transcribe_voice_file(test_path)
        print(f"\n📝 Result: {result}")
    else:
        print("Usage: python -m execution.transcribe_voice <path_to_audio_file>")
        print("Example: python -m execution.transcribe_voice .tmp/test_recording.wav")
