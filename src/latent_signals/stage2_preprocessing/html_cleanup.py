"""HTML and markdown cleanup, text normalization."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    """Strip HTML, normalize whitespace, remove markdown artifacts."""
    # Strip HTML tags
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(separator=" ")

    # Remove markdown links but keep text: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # Remove markdown formatting
    text = re.sub(r"[*_~`]{1,3}", "", text)

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
