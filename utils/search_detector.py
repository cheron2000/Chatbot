"""Filter out purely conversational messages that don't need web search."""

SKIP_PHRASES = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "yes",
    "no",
    "sure",
    "cool",
    "great",
    "nice",
    "bye",
    "goodbye",
    "good morning",
    "good night",
    "good evening",
    "how are you",
    "what's up",
    "sup",
    "lol",
    "haha",
    "wow",
}


def should_skip_search(message: str) -> bool:
    """Return True for short conversational messages that don't need web search."""
    clean = message.strip().lower().rstrip("!?.")
    if clean in SKIP_PHRASES:
        return True
    if len(clean) < 5:
        return True
    return False
