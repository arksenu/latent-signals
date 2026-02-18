"""Language detection filter."""

from __future__ import annotations

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException


def detect_language(text: str) -> str:
    """Detect the language of a text string. Returns ISO 639-1 code."""
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def is_target_language(text: str, target: str = "en") -> bool:
    """Check if text is in the target language."""
    return detect_language(text) == target
