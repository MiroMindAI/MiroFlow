# Audio Tools - Open Source (`audio_mcp_server_os.py`)

The Audio MCP Server (Open Source) enables audio transcription using open-source Whisper models. It provides comprehensive audio-to-text conversion with support for multiple audio formats, local files, and URLs.

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Audio Transcription**: High-quality speech-to-text conversion
    - **Multi-Format Support**: MP3, WAV, M4A, AAC, OGG, FLAC, WMA formats
    - **Flexible Input**: Local file paths and web URLs
    - **Open-Source Model Support**: Whisper-Large-v3-Turbo with automatic processing

---

## Environment Variables

!!! warning "Configuration Location"
    The `audio_mcp_server_os.py` reads environment variables that are passed through the `tool-audio-os.yaml` configuration file, not directly from `.env` file.

**Open-Source Model Configuration:**

- `WHISPER_API_KEY`: Required API key for the open-source Whisper service
- `WHISPER_BASE_URL`: Base URL for the Whisper service API endpoint
- `WHISPER_MODEL_NAME`: Model name (default: `openai/whisper-large-v3-turbo`)

**Example Configuration:**
```bash
# API for Open-Source Audio Transcription Tool (for benchmark testing)
WHISPER_MODEL_NAME="openai/whisper-large-v3-turbo"
WHISPER_API_KEY=your_whisper_key
WHISPER_BASE_URL="https://your_whisper_base_url/v1"
```

---

## Local Deployment

### Using vLLM Server

For optimal performance with the Whisper-Large-v3-Turbo model, deploy using vLLM:

```bash
pip install vllm==0.10.0
pip install vllm[audio]
vllm serve /path/to/whisper \
  --served-model-name whisper-large-v3-turbo \
  --task transcription
```

### Configuration for Local Deployment

When using local deployment, configure your environment variables:

```bash
WHISPER_MODEL_NAME="openai/whisper-large-v3-turbo"
WHISPER_API_KEY="dummy_key"  # Not required for local deployment
WHISPER_BASE_URL="http://localhost:8000/v1"
```

---

## Function Reference

The following function is provided by the `audio_mcp_server_os.py` MCP tool and can be called by agents:

### `audio_transcription(audio_path_or_url: str)`

Transcribe audio files to text using open-source Whisper models. Supports both local files and web URLs with automatic format detection and processing.

**Parameters:**

- `audio_path_or_url`: Local file path (accessible to server) or web URL

**Returns:**

- `str`: The transcription of the audio file

**Supported Audio Formats:**
- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- AAC (.aac)
- OGG (.ogg)
- FLAC (.flac)
- WMA (.wma)

## Usage Examples

### Local File Transcription
```python
# Local file transcription
result = audio_transcription(
    audio_path_or_url="/path/to/audio.mp3"
)
```

### URL-based Transcription
```python
# URL transcription
result = audio_transcription(
    audio_path_or_url="https://example.com/audio.wav"
)
```

### Meeting Recording Transcription
```python
result = audio_transcription(
    audio_path_or_url="meeting_recording.m4a"
)
```

### Podcast Transcription
```python
result = audio_transcription(
    audio_path_or_url="podcast_episode.mp3"
)
```

---

## Technical Implementation

### Audio Processing Pipeline

1. **Input Validation**: Checks if input is local file or URL
2. **Format Detection**: Determines audio format from extension or content type
3. **File Handling**: Downloads URL files to temporary storage with proper extensions
4. **API Request**: Sends audio file to Whisper model for transcription
5. **Cleanup**: Removes temporary files after processing
6. **Response Processing**: Returns transcription text

### Error Handling

- **File Access Errors**: Graceful handling of inaccessible local files
- **Network Errors**: Robust URL fetching with retry logic (up to 3 attempts)
- **Format Errors**: Automatic format detection and validation
- **API Errors**: Clear error reporting for service issues
- **Sandbox Restrictions**: Prevents access to sandbox files with clear error messages

### Retry Logic

- **Maximum Retries**: 3 attempts for failed requests
- **Exponential Backoff**: 5, 10, 20 second delays between retries
- **Network Resilience**: Handles temporary network issues and service unavailability

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
