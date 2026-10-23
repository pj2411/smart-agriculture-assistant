"""Supported JalSaathi speech and assistant languages."""

SUPPORTED_LANGUAGES = {
    "hi-IN": {"name": "Hindi", "stt_code": "hi-IN", "tts_code": "hi", "default_voice": "Deepak"},
    "en-IN": {"name": "English", "stt_code": "en-IN", "tts_code": "en-IN", "default_voice": "Yashvi"},
    "pa-IN": {"name": "Punjabi", "stt_code": "pa-IN", "tts_code": "pa", "default_voice": "Zayan"},
    "bn-IN": {"name": "Bengali", "stt_code": "bn-IN", "tts_code": "bn", "default_voice": "Kirra"},
    "mr-IN": {"name": "Marathi", "stt_code": "mr-IN", "tts_code": "mr", "default_voice": "Omkar"},
}

SUPPORTED_LANGUAGE_CODES = frozenset(SUPPORTED_LANGUAGES)


def get_language(language_code: str):
    return SUPPORTED_LANGUAGES.get(language_code)
