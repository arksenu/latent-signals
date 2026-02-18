"""Filter low-information posts: bots, gratitude, meta-discussion."""

from __future__ import annotations

import re

# Known bot usernames (case-insensitive partial matches)
BOT_PATTERNS = [
    r"bot\b",
    r"automoderator",
    r"remindmebot",
    r"commonmisspellingbot",
    r"sneakpeekbot",
    r"repostsleuthbot",
    r"haikusbot",
]
_BOT_RE = re.compile("|".join(BOT_PATTERNS), re.IGNORECASE)

# Gratitude / low-info patterns (match entire text after strip)
GRATITUDE_PATTERNS = [
    r"^thanks?\.?!?\s*$",
    r"^thank you\.?!?\s*$",
    r"^thx\.?!?\s*$",
    r"^ty\.?!?\s*$",
    r"^great\.?!?\s*$",
    r"^nice\.?!?\s*$",
    r"^awesome\.?!?\s*$",
    r"^this\.?\s*$",
    r"^same\.?\s*$",
    r"^agreed\.?\s*$",
    r"^\+1\.?\s*$",
    r"^lol\.?\s*$",
    r"^upvoted?\.?\s*$",
    r"^saved?\.?\s*$",
    r"^bump\.?\s*$",
    r"^deleted\s*$",
    r"^\[deleted\]\s*$",
    r"^\[removed\]\s*$",
]
_GRATITUDE_RE = re.compile("|".join(GRATITUDE_PATTERNS), re.IGNORECASE)

# Bot signature phrases found in the body text itself
BOT_BODY_PATTERNS = [
    r"^just a quick heads.?up",
    r"^i'?m a bot",
    r"i am a bot",
    r"this action was performed automatically",
    r"beep\.?\s*boop",
    r"^common misspelling",
]
_BOT_BODY_RE = re.compile("|".join(BOT_BODY_PATTERNS), re.IGNORECASE)


def is_noise(text: str, author: str | None = None) -> bool:
    """Return True if the post is low-information noise."""
    stripped = text.strip()

    # Very short content that matches gratitude patterns
    if len(stripped) < 100 and _GRATITUDE_RE.match(stripped):
        return True

    # Bot author
    if author and _BOT_RE.search(author):
        return True

    # Bot body signatures
    if _BOT_BODY_RE.search(stripped[:200]):
        return True

    return False
