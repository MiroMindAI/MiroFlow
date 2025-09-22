# Vision Tools (`vision_mcp_server.py`)

The Vision MCP Server enables OCR + Visual Question Answering (VQA) over images and multimodal understanding of YouTube videos, with pluggable backends (Anthropic, OpenAI, Google Gemini).

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Visual Question Answering**: OCR and VQA analysis of images with dual-pass processing
    - **YouTube Video Analysis**: Audio and visual analysis of public YouTube videos
    - **Multi-Backend Support**: Configurable vision backends (Anthropic, OpenAI, Gemini)

---

## Environment Variables

!!! warning "Configuration Location"
    The `vision_mcp_server.py` reads environment variables that are passed through the `tool-image-video.yaml` configuration file, not directly from `.env` file.

**Vision Backend Control:**

- `ENABLE_CLAUDE_VISION`: `"true"` to allow Anthropic Vision backend
- `ENABLE_OPENAI_VISION`: `"true"` to allow OpenAI Vision backend

**Anthropic Configuration:**

- `ANTHROPIC_API_KEY`: Required API key for Anthropic services
- `ANTHROPIC_BASE_URL`: Default = `https://api.anthropic.com`
- `ANTHROPIC_MODEL_NAME`: Default = `claude-3-7-sonnet-20250219`

**OpenAI Configuration:**

- `OPENAI_API_KEY`: Required API key for OpenAI services
- `OPENAI_BASE_URL`: Default = `https://api.openai.com/v1`
- `OPENAI_MODEL_NAME`: Default = `gpt-4o`

**Gemini Configuration:**

- `GEMINI_API_KEY`: Required API key for Google Gemini services
- `GEMINI_MODEL_NAME`: Default = `gemini-2.5-pro`

---

## Function Reference

The following functions are provided by the `vision_mcp_server.py` MCP tool and can be called by agents:

### `visual_question_answering(image_path_or_url: str, question: str)`

Ask questions about an image using a dual-pass analysis approach for comprehensive understanding.

!!! tip "Two-Pass Analysis"
    This function runs **two passes**:
    
    1. **OCR pass** using the selected vision backend with a meticulous extraction prompt
    2. **VQA pass** that analyzes the image and cross-checks against OCR text

**Parameters:**

- `image_path_or_url`: Local path (accessible to server) or web URL. HTTP URLs are auto-upgraded/validated to HTTPS for some backends
- `question`: The user's question about the image

**Returns:**

- `str`: Concatenated text with:
    - `OCR results: ...`
    - `VQA result: ...`

**Features:**

- Automatic MIME detection, reads magic bytes, falls back to extension, final default is `image/jpeg`
- Multi-backend support for different vision models
- Cross-validation between OCR and VQA results

---

### `visual_audio_youtube_analyzing(url: str, question: str = "", provide_transcribe: bool = False)`

Analyze **public YouTube videos** (audio + visual). Supports watch pages, Shorts, and Live VODs.

!!! note "Supported URL Patterns"
    Accepted URL patterns: `youtube.com/watch`, `youtube.com/shorts`, `youtube.com/live`

**Parameters:**

- `url`: YouTube video URL (publicly accessible)
- `question` (optional): A specific question about the video. You can scope by time using `MM:SS` or `MM:SS-MM:SS` (e.g., `01:45`, `03:20-03:45`)
- `provide_transcribe` (optional, default `False`): If `True`, returns a **timestamped transcription** including salient events and brief visual descriptions

**Returns:**

- `str`: Transcription of the video (if requested) and answer to the question

**Features:**

- **Gemini-powered** video analysis (requires `GEMINI_API_KEY`)
- Dual mode: full transcript, targeted Q&A, or both
- Time-scoped question answering for specific video segments
- Support for multiple YouTube video formats

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI