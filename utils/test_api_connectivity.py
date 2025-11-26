from __future__ import annotations
import os
import json
import requests
from openai import OpenAI
from typing import Any, Dict


def _ok(data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "ok"}
    if data:
        out.update(data)
    return out

def _skipped(reason: str) -> Dict[str, Any]:
    return {"status": "skipped", "reason": reason}

def _failed(error: str) -> Dict[str, Any]:
    return {"status": "failed", "error": error}

def check_llm_gateway() -> Dict[str, Any]:
    """Test main LLM gateway."""
    api_key = os.getenv("LLM_GATEWAY_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = (
        os.getenv("LLM_GATEWAY_URL")
        or os.getenv("OPENROUTER_BASE_URL")
        or "https://openrouter.ai/api/v1"
    ).rstrip("/")
    model = os.getenv("LLM_GATEWAY_MODEL") or os.getenv("OPENROUTER_MODEL_NAME")

    if not api_key or not model:
        return _skipped("Missing LLM_GATEWAY_API_KEY/OPENROUTER_API_KEY or model name")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        # basic shape check
        _ = resp.choices[0].message.content
        return _ok({"model": model, "base_url": base_url})
    except Exception as e:  # noqa: BLE001
        return _failed(str(e))

def check_openai_direct() -> Dict[str, Any]:
    """Test direct OpenAI-style API (if configured)."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL_NAME", "gpt-4.1")

    if not api_key:
        return _skipped("Missing OPENAI_API_KEY")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        _ = resp.choices[0].message.content
        return _ok({"model": model, "base_url": base_url})
    except Exception as e:  # noqa: BLE001
        return _failed(str(e))

def check_serper() -> Dict[str, Any]:
    """Test Serper search API."""
    api_key = os.getenv("SERPER_API_KEY")
    base_url = os.getenv("SERPER_BASE_URL", "https://google.serper.dev").rstrip("/")

    if not api_key:
        return _skipped("Missing SERPER_API_KEY")

    try:
        resp = requests.post(
            base_url,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": "MiroFlow connectivity test", "num": 1},
            timeout=20,
        )
        if not resp.ok:
            return _failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
        _ = resp.json()
        return _ok({"base_url": base_url})
    except Exception as e:  # noqa: BLE001
        return _failed(str(e))

def check_jina() -> Dict[str, Any]:
    """Test Jina Reader API."""
    api_key = os.getenv("JINA_API_KEY")
    base_url = os.getenv("JINA_BASE_URL", "https://r.jina.ai").rstrip("/")

    if not api_key:
        return _skipped("Missing JINA_API_KEY")

    try:
        # Use a simple URL fetch to test connectivity
        test_url = "https://github.com/MiroMindAI/MiroFlow"
        resp = requests.get(
            base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"url": test_url},
            timeout=20,
        )
        if not resp.ok:
            return _failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return _ok({"base_url": base_url})
    except Exception as e:  # noqa: BLE001
        return _failed(str(e))

def _check_generic_chat_service(
    api_key_env: str,
    base_url_env: str,
    model_env: str,
    default_base: str | None = None,
) -> Dict[str, Any]:
    api_key = os.getenv(api_key_env)
    base_url = os.getenv(base_url_env, default_base or "").rstrip("/")
    model = os.getenv(model_env)

    if not api_key or not base_url or not model:
        return _skipped(f"Missing {api_key_env}/{base_url_env}/{model_env}")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        _ = resp.choices[0].message.content
        return _ok({"model": model, "base_url": base_url})
    except Exception as e:  # noqa: BLE001
        return _failed(str(e))

def check_reasoning_os() -> Dict[str, Any]:
    return _check_generic_chat_service(
        api_key_env="REASONING_API_KEY",
        base_url_env="REASONING_BASE_URL",
        model_env="REASONING_MODEL_NAME",
    )

def check_vision_os() -> Dict[str, Any]:
    return _check_generic_chat_service(
        api_key_env="VISION_API_KEY",
        base_url_env="VISION_BASE_URL",
        model_env="VISION_MODEL_NAME",
    )

def check_audio_os() -> Dict[str, Any]:
    api_key = os.getenv("WHISPER_API_KEY")
    base_url = os.getenv("WHISPER_BASE_URL", "").rstrip("/")
    model = os.getenv("WHISPER_MODEL_NAME")

    if not api_key or not base_url or not model:
        return _skipped("Missing WHISPER_API_KEY/WHISPER_BASE_URL/WHISPER_MODEL_NAME")

    try:
        # We don't send a real file here to avoid side effects; just test that the
        # endpoint is reachable by hitting the base URL.
        resp = requests.get(
            base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        if not resp.ok:
            return _failed(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return _ok({"base_url": base_url, "model": model})
    except Exception as e:  # noqa: BLE001
        return _failed(str(e))

def main() -> None:
    report: Dict[str, Dict[str, Any]] = {
        "llm_gateway": check_llm_gateway(),
        "openai_direct": check_openai_direct(),
        "serper": check_serper(),
        "jina": check_jina(),
        "reasoning_os": check_reasoning_os(),
        "vision_os": check_vision_os(),
        "audio_os": check_audio_os(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    main()
