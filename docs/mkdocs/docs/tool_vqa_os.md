# Vision Tools - Open Source (`vision_mcp_server_os.py`)

The Vision MCP Server (Open Source) enables Visual Question Answering (VQA) over images using open-source vision-language models. It provides comprehensive image analysis with support for local files and URLs.

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Visual Question Answering**: Comprehensive image analysis and question answering
    - **Multi-Format Support**: JPEG, PNG, GIF image formats
    - **Flexible Input**: Local file paths and web URLs
    - **Open-Source Model Support**: Qwen2.5-VL-72B-Instruct with automatic encoding

---

## Environment Variables

!!! warning "Configuration Location"
    The `vision_mcp_server_os.py` reads environment variables that are passed through the `tool-image-video-os.yaml` configuration file, not directly from `.env` file.

**Open-Source Model Configuration:**

- `VISION_API_KEY`: Required API key for the open-source vision service
- `VISION_BASE_URL`: Base URL for the vision service API endpoint
- `VISION_MODEL_NAME`: Model name (default: `Qwen/Qwen2.5-VL-72B-Instruct`)

**Example Configuration:**
```bash
# API for Open-Source VQA Tool (for benchmark testing)
VISION_MODEL_NAME="Qwen/Qwen2.5-VL-72B-Instruct"
VISION_API_KEY=your_vision_key
VISION_BASE_URL="https://your_vision_base_url/v1/chat/completions"
```

---

## Local Deployment

### Using SGLang Server

For optimal performance with the Qwen2.5-VL-72B-Instruct model, deploy using SGLang (suggested SGLang version is `0.5.2`, as lower versions have potential issues with the model):

```bash
python3 -m sglang.launch_server \
  --model-path /path/to/Qwen2.5-VL-72B-Instruct \
  --tp 8 --host 0.0.0.0 --port 1234 \
  --trust-remote-code --enable-metrics \
  --log-level debug --log-level-http debug \
  --log-requests --log-requests-level 2 --show-time-cost
```

### Configuration for Local Deployment

When using local deployment, configure your environment variables:

```bash
VISION_MODEL_NAME="Qwen/Qwen2.5-VL-72B-Instruct"
VISION_API_KEY="dummy_key"  # Not required for local deployment
VISION_BASE_URL="http://localhost:1234/v1/chat/completions"
```

---

## Function Reference

The following function is provided by the `vision_mcp_server_os.py` MCP tool and can be called by agents:

### `visual_question_answering(image_path_or_url: str, question: str)`

Ask questions about images using open-source vision-language models. Supports both local files and web URLs with automatic format detection and encoding.

**Parameters:**

- `image_path_or_url`: Local file path (accessible to server) or web URL
- `question`: The user's question about the image

**Returns:**

- `str`: The model's answer to the image-related question

**Supported Image Formats:**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- Default fallback to JPEG for unknown formats

## Usage Examples

### Image Analysis
```python
# Local file analysis
result = visual_question_answering(
    image_path_or_url="/path/to/image.jpg",
    question="What objects can you see in this image?"
)

# URL analysis
result = visual_question_answering(
    image_path_or_url="https://example.com/image.png",
    question="Describe the scene in detail."
)
```

### OCR and Text Extraction
```python
result = visual_question_answering(
    image_path_or_url="document.jpg",
    question="Extract all the text from this document."
)
```

### Object Detection and Counting
```python
result = visual_question_answering(
    image_path_or_url="scene.jpg",
    question="Count how many people are in this image and describe their activities."
)
```

### Technical Diagram Analysis
```python
result = visual_question_answering(
    image_path_or_url="diagram.png",
    question="Explain this technical diagram and identify the key components."
)
```

---

## Technical Implementation

### Image Processing Pipeline

1. **Input Validation**: Checks if input is local file or URL
2. **Format Detection**: Determines MIME type from extension or headers
3. **Encoding**: Converts images to Base64 for API transmission
4. **API Request**: Sends structured request to vision model
5. **Response Processing**: Extracts and returns model response

### Error Handling

- **File Access Errors**: Graceful handling of inaccessible local files
- **Network Errors**: Robust URL fetching with proper error messages
- **Format Errors**: Fallback MIME type detection for unknown formats
- **API Errors**: Clear error reporting for service issues

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
