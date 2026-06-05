"""
Response formatter for the AI Python Tutor.
Formats LLM output into a consistent dict structure and detects the Python topic.
"""

import re
from app.topics import SUPPORTED_TOPICS

# Keyword aliases that map to a canonical topic (canonical values match SUPPORTED_TOPICS casing).
# Order matters: more-specific / longer aliases must come before shorter ones that could
# be substrings of them (e.g. "fastapi" before "api", "recursion" before "function").
_TOPIC_ALIASES: list[tuple[str, str]] = [
    # --- algorithms (must come before "function" alias to avoid "recursion" → functions) ---
    ("recursion", "algorithms"),
    ("algorithm", "algorithms"),
    ("sorting", "algorithms"),
    ("searching", "algorithms"),
    # --- FastAPI / Flask (must come before bare "api" alias to avoid "fastapi" → APIs) ---
    ("fastapi", "FastAPI basics"),
    ("flask", "Flask basics"),
    # --- loops (must come before "oop" alias to avoid "loop" → OOP) ---
    ("for loop", "loops"),
    ("while loop", "loops"),
    ("loop", "loops"),
    # --- other topics ---
    ("variable", "variables"),
    ("data type", "data types"),
    ("function", "functions"),
    ("def ", "functions"),
    ("class ", "OOP"),
    ("object", "OOP"),
    ("inheritance", "OOP"),
    ("open(", "file handling"),
    ("exception", "exception handling"),
    ("try:", "exception handling"),
    ("except", "exception handling"),
    ("import", "modules"),
    ("module", "modules"),
    ("package", "modules"),
    ("api", "APIs"),
    ("requests", "APIs"),
    ("list", "data structures"),
    ("dict", "data structures"),
    ("dictionary", "data structures"),
    ("tuple", "data structures"),
    ("stack", "data structures"),
    ("queue", "data structures"),
    ("sort", "algorithms"),
    ("search", "algorithms"),
]

# Sort supported topics longest-first so that "FastAPI basics" is checked before "APIs",
# and "exception handling" before "modules", etc.
# Each entry is (compiled regex pattern, canonical topic string).
_SORTED_TOPIC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b' + re.escape(t) + r'\b', re.IGNORECASE), t)
    for t in sorted(SUPPORTED_TOPICS, key=len, reverse=True)
]


def _detect_topic(content: str) -> str | None:
    """
    Scan content for topic keywords and return the first matched canonical topic.
    Returns None if no supported topic is detected.

    Strategy:
    1. Check direct topic names (longest first, case-insensitive).
    2. Fall back to alias list (ordered so specific aliases precede generic ones).
    """
    lowered = content.lower()

    # 1. Direct topic name matching (longest topic first, whole-word, case-insensitive)
    for pattern, topic_canonical in _SORTED_TOPIC_PATTERNS:
        if pattern.search(content):
            return topic_canonical

    # 2. Alias matching (list order is intentional — see comments above)
    for alias, canonical in _TOPIC_ALIASES:
        if alias in lowered:
            return canonical

    return None


def format_response(content: str, intent: str) -> dict:
    """
    Format an LLM response into a consistent response dict.

    Returns a dict with keys:
        intent  (str)       — the classified intent
        content (str)       — the markdown-formatted response body
        topic   (str|None)  — detected Python topic, or None
    """
    topic = _detect_topic(content)
    return {
        "intent": intent,
        "content": content,
        "topic": topic,
    }
