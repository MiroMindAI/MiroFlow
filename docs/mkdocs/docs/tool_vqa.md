# Vision Tools (`vision_mcp_server.py`)

The Vision MCP Server enables OCR + Visual Question Answering (VQA) over images and multimodal understanding of YouTube videos, with pluggable backends (Anthropic, OpenAI, Google Gemini).

---

## Environment Variables
!!! warning "Where to Modify"
    The `vision_mcp_server.py` reads environment variables that are passed through the `tool-image-video.yaml` configuration file, not directly from `.env` file.
- Vision Backend Control:
    - `ENABLE_CLAUDE_VISION`: `"true"` to allow Anthropic Vision backend.
    - `ENABLE_OPENAI_VISION`: `"true"` to allow OpenAI Vision backend.
- Anthropic Configuration:
    - `ANTHROPIC_API_KEY`
    -  `ANTHROPIC_BASE_URL` : default = `https://api.anthropic.com`
    -  `ANTHROPIC_MODEL_NAME` : default = `claude-3-7-sonnet-20250219`
- OpenAI Configuration:
    - `OPENAI_API_KEY`
    -  `OPENAI_BASE_URL` : default = `https://api.openai.com/v1`
    -  `OPENAI_MODEL_NAME` : default = `gpt-4o`
- Gemini Configuration:
    - `GEMINI_API_KEY`
    -  `GEMINI_MODEL_NAME` : default = `gemini-2.5-pro`


---

## `visual_question_answering(image_path_or_url: str, question: str)`
Ask questions about an image. Runs **two passes**:

1. **OCR pass** using the selected vision backend with a meticulous extraction prompt.

2. **VQA pass** that analyzes the image and cross-checks against OCR text.

**Parameters**

- `image_path_or_url`: Local path (accessible to server) or web URL. HTTP URLs are auto-upgraded/validated to HTTPS for some backends.
- `question`: The user’s question about the image.

**Returns**

- `str`: Concatenated text with:
    - `OCR results: ...`
    - `VQA result: ...`

**Features**

- Automatic MIME detection, reads magic bytes, falls back to extension, final default is `image/jpeg`.

---

## `visual_audio_youtube_analyzing(url: str, question: str = "", provide_transcribe: bool = False)`
Analyze **public YouTube videos** (audio + visual). Supports watch pages, Shorts, and Live VODs.

- Accepted URL patterns: `youtube.com/watch`, `youtube.com/shorts`, `youtube.com/live`.

**Parameters**

- `url`: YouTube video URL (publicly accessible).
- `question` (optional): A specific question about the video. You can scope by time using `MM:SS` or `MM:SS-MM:SS` (e.g., `01:45`, `03:20-03:45`).
- `provide_transcribe` (optional, default `False`): If `True`, returns a **timestamped transcription** including salient events and brief visual descriptions.

**Returns**

- `str`: transcription of the video (if asked) and answer to the question.

**Features**

- **Gemini-powered** video analysis (requires `GEMINI_API_KEY`).
- Dual mode: full transcript, targeted Q&A, or both.

---

**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI
