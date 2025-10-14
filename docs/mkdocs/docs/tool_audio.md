# Audio Tools (`tool-audio`)

Audio processing capabilities including transcription and audio-based question answering.

---

## Configuration

```yaml title="Agent Configuration"
main_agent:
  tool_config: 
    - tool-audio
```

**Environment Variables:**

- `OPENAI_API_KEY`: **Required**. OpenAI API key
- `OPENAI_BASE_URL`: API base URL. Default: `https://api.openai.com/v1`
- `OPENAI_TRANSCRIPTION_MODEL_NAME`: Default: `gpt-4o-transcribe`
- `OPENAI_AUDIO_MODEL_NAME`: Default: `gpt-4o-audio-preview`

---

## Function Reference

### `audio_transcription(audio_path_or_url: str)`

Transcribe audio file to text using OpenAI's Whisper models.

**Parameters:**

- `audio_path_or_url`: Local file path or URL
  - Supported formats: MP3, WAV, M4A, FLAC, OGG, WebM
  - Not supported: E2B sandbox paths, YouTube URLs

**Returns:**

- `str`: Full transcription of the audio file

**Example:**

```python
# Transcribe local audio
transcription = await audio_transcription("/data/meeting.mp3")

# Transcribe from URL
transcription = await audio_transcription("https://example.com/podcast.wav")
```

---

### `audio_question_answering(audio_path_or_url: str, question: str)`

Answer questions based on audio content using GPT-4o Audio.

**Parameters:**

- `audio_path_or_url`: Local file path or URL (same formats as transcription)
- `question`: Question to answer about the audio content

**Returns:**

- `str`: Answer with audio duration information

**Example:**

```python
# Ask about content
answer = await audio_question_answering(
    "/data/lecture.mp3", 
    "What are the main topics discussed?"
)

# Get summary
answer = await audio_question_answering(
    "https://example.com/interview.wav",
    "Summarize the key points."
)
```

**Important Notes:**

- Cannot access E2B sandbox files (`/home/user/`)
- YouTube URLs not supported (use VQA tools instead)
- Includes audio duration in response

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
