"""Server-side provider adapters for JalSaathi.

The adapters return honest configuration/provider errors. They never create
mock transcripts, canned model responses, or placeholder audio.
"""

import base64
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

from languages import get_language


class ProviderError(RuntimeError):
    def __init__(self, category: str, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.category = category
        self.status_code = status_code


def provider_status() -> Dict[str, Any]:
    return {
        "llm": {"provider": os.getenv("LLM_PROVIDER", "openrouter"), "configured": bool(os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_MODEL"))},
        "stt": {"provider": os.getenv("STT_PROVIDER", "gnani"), "configured": bool(os.getenv("GNANI_STT_API_KEY_ID"))},
        "tts": {"provider": os.getenv("TTS_PROVIDER", "gnani"), "configured": bool(os.getenv("GNANI_TTS_API_KEY"))},
    }


def _json_request(url: str, body: Dict[str, Any], headers: Dict[str, str], timeout: int = 45) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read(512).decode("utf-8", errors="replace")
        raise ProviderError("provider_http_error", f"Provider returned HTTP {exc.code}: {detail[:240]}", exc.code) from exc
    except error.URLError as exc:
        raise ProviderError("provider_network_error", f"Provider network request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ProviderError("provider_timeout", "Provider request timed out.") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProviderError("provider_invalid_response", "Provider returned an invalid JSON response.") from exc


def get_llm_response(message: str, history: Optional[List[Dict[str, str]]], language_code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    if provider != "openrouter":
        raise ProviderError("provider_not_supported", f"Configured LLM provider '{provider}' is not implemented in this build.")
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    if not api_key or not model:
        raise ProviderError("not_configured", "OpenRouter is not configured. Set OPENROUTER_API_KEY and OPENROUTER_MODEL.")
    language = get_language(language_code)
    if not language:
        raise ProviderError("unsupported_language", f"Unsupported assistant language: {language_code}.")

    context_text = json.dumps(context or {}, ensure_ascii=False)
    system = (
        "You are JalSaathi, a concise and respectful farm assistant. "
        f"Reply only in {language['name']} ({language_code}) using simple language. "
        "Do not translate the answer into another language unless the farmer asks to switch. "
        "Use only the supplied context. Never invent sensor readings, crop thresholds, savings, weather, or device status. "
        "Scenario readings are simulated test values and must be identified as simulated. "
        "If no live device is connected, say current sensor readings are unavailable. "
        "Numeric crop targets are valid only when the server provides a verified source-backed profile. "
        "Give advisory information only; never claim that a physical actuator was controlled.\n\n"
        f"APP CONTEXT: {context_text}"
    )
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for item in (history or [])[-12:]:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message.strip()})
    payload = _json_request(
        "https://openrouter.ai/api/v1/chat/completions",
        {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 1500},
        {"Authorization": f"Bearer {api_key}", "HTTP-Referer": os.getenv("APP_PUBLIC_URL", ""), "X-OpenRouter-Title": "JalSaathi"},
    )
    try:
        choice_msg = payload["choices"][0]["message"]
        reply = choice_msg.get("content") or choice_msg.get("reasoning") or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("provider_invalid_response", "OpenRouter returned no usable assistant message.") from exc
    return {"reply": str(reply).strip(), "provider": "openrouter", "model": model, "language_code": language_code}


def _multipart(audio_bytes: bytes, filename: str, content_type: str, fields: Dict[str, str]) -> Tuple[bytes, str]:
    boundary = f"----JalSaathi{uuid.uuid4().hex}"
    chunks: List[bytes] = []
    for name, value in fields.items():
        chunks.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), value.encode(), b"\r\n"])
    chunks.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="audio_file"; filename="{filename}"\r\n'.encode(), f"Content-Type: {content_type}\r\n\r\n".encode(), audio_bytes, b"\r\n", f"--{boundary}--\r\n".encode()])
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def transcribe_audio(audio_bytes: bytes, filename: str, content_type: str, language_code: str) -> Dict[str, Any]:
    api_key = os.getenv("GNANI_STT_API_KEY_ID", "").strip()
    if not api_key:
        raise ProviderError("not_configured", "Gnani STT is not configured. Set GNANI_STT_API_KEY_ID.")
    language = get_language(language_code)
    if not language:
        raise ProviderError("unsupported_language", f"Unsupported STT language: {language_code}.")
    stt_code = language["stt_code"]
    body, multipart_type = _multipart(audio_bytes, filename, content_type, {
        "language_code": stt_code,
        "preferred_language": stt_code,
        "format": os.getenv("GNANI_STT_FORMAT", "transcribe"),
        "itn_native_numerals": "true",
    })
    req = request.Request(os.getenv("GNANI_STT_ENDPOINT", "https://api.vachana.ai/stt/v3"), data=body, headers={"Content-Type": multipart_type, "X-API-Key-ID": api_key}, method="POST")
    try:
        with request.urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read(512).decode("utf-8", errors="replace")
        raise ProviderError("provider_http_error", f"Gnani STT returned HTTP {exc.code}: {detail[:240]}", exc.code) from exc
    except error.URLError as exc:
        raise ProviderError("provider_network_error", f"Gnani STT network request failed: {exc.reason}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProviderError("provider_invalid_response", "Gnani STT returned an invalid response.") from exc
    transcript = payload.get("transcript") or payload.get("text") or (payload.get("data") or {}).get("transcript")
    if not transcript:
        raise ProviderError("provider_invalid_response", "Gnani STT returned no transcript.")
    return {"transcript": str(transcript), "language_code": language_code, "provider": "gnani"}


def synthesize_speech(text: str, language_code: str) -> Tuple[bytes, str]:
    api_key = os.getenv("GNANI_TTS_API_KEY", "").strip()
    if not api_key:
        raise ProviderError("not_configured", "Gnani TTS is not configured. Set GNANI_TTS_API_KEY.")
    language_info = get_language(language_code)
    if not language_info:
        raise ProviderError("unsupported_language", f"Unsupported TTS language: {language_code}.")
    env_suffix = language_code.replace("-", "_").upper()
    language = os.getenv(f"GNANI_TTS_LANGUAGE_{env_suffix}", "").strip() or language_info["tts_code"]
    voice = os.getenv(f"GNANI_TTS_VOICE_{env_suffix}", "").strip() or os.getenv("GNANI_TTS_VOICE", "").strip() or language_info["default_voice"]
    payload = {"model": os.getenv("GNANI_TTS_MODEL", "timbre-2.5"), "language": language, "voice": voice, "sample_rate": int(os.getenv("GNANI_TTS_SAMPLE_RATE", "48000")), "text": text.strip()}
    req = request.Request(os.getenv("GNANI_TTS_ENDPOINT", "https://api.gnani.ai/v1/tts/inference"), data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    try:
        with request.urlopen(req, timeout=45) as response:
            raw = response.read()
            content_type = response.headers.get_content_type() or "audio/wav"
    except error.HTTPError as exc:
        detail = exc.read(512).decode("utf-8", errors="replace")
        raise ProviderError("provider_http_error", f"Gnani TTS returned HTTP {exc.code}: {detail[:240]}", exc.code) from exc
    except error.URLError as exc:
        raise ProviderError("provider_network_error", f"Gnani TTS network request failed: {exc.reason}") from exc
    if content_type == "application/json":
        try:
            response_json = json.loads(raw.decode("utf-8"))
            encoded = response_json.get("audio") or response_json.get("audio_base64") or (response_json.get("data") or {}).get("audio")
            if encoded:
                raw = base64.b64decode(encoded)
                content_type = "audio/wav"
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderError("provider_invalid_response", "Gnani TTS returned an invalid audio response.") from exc
    if not raw:
        raise ProviderError("provider_invalid_response", "Gnani TTS returned empty audio.")
    return raw, content_type
