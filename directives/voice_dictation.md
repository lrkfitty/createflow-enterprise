# Voice Dictation Directive

## Goal
Allow users to speak their creative brief aloud instead of typing. Audio is captured in the browser via Streamlit's native `st.audio_input` and transcribed via OpenAI Whisper, then fed directly into the NL Art Director (`parse_intent.py`).

## Inputs
- **audio_bytes** (bytes): Raw audio captured by `st.audio_input()`. Streamlit returns a file-like `BytesIO` object.
- **language** (str, optional): ISO-639-1 code (e.g. `"en"`) to improve Whisper accuracy. Auto-detected if not provided.

## Tools
1. `execution/transcribe_voice.py` → `transcribe_voice(audio_bytes, language)` — sends audio to Whisper API, returns text string.
2. `execution/parse_intent.py` → `parse_intent(brief)` — maps transcribed text to assets (downstream).

## Output
- Transcribed text string, populated into the brief text area in the UI.
- User sees: *"🎙️ I heard: [transcription]"* confirmation before anything generates.

## Whisper API Details
- **Model**: `whisper-1` (only model available via API as of 2026).
- **Formats**: WAV, MP3, MP4, MPEG, MPGA, M4A, OGG, OGA, WEBM. Streamlit's `st.audio_input` outputs WEBM or WAV depending on browser — both work.
- **Max file size**: 25MB (Whisper API limit). Voice briefs are typically <1MB, no issue.
- **API key**: `OPENAI_API_KEY` (already in `.env`).
- **Cost**: ~$0.006/minute. A typical 10-second brief costs ~$0.001.

## Edge Cases & Learnings
- **Streamlit version**: `st.audio_input` requires Streamlit ≥ 1.34. Check with `streamlit --version`. If older, install `streamlit-mic-recorder` as fallback.
- **No microphone detected**: `st.audio_input` renders as disabled in the browser. Show a fallback note: "Mic not available — type your brief above."
- **Empty audio**: `transcribe_voice()` returns `""`. App should detect this and show: "No audio detected — please try again."
- **Background noise**: Whisper is robust, but very noisy environments may degrade accuracy. Show the transcription for user confirmation before proceeding.
- **Non-English input**: Whisper auto-detects language and transcribes. Works well for most languages. Set `language` parameter for consistent results.
- **Temp file cleanup**: `transcribe_voice.py` always deletes the temp WAV file after the Whisper call, even on error.

## Integration Point
Art Director tab in `app.py`:
1. 🎙️ mic button via `st.audio_input()`
2. On recording: `transcribe_voice(audio_bytes.read())` called
3. Result populates `st.session_state.art_director_brief`
4. User confirms/edits in the text area below
5. Normal flow: `parse_intent()` → confirm → generate
