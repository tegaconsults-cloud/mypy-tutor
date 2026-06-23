"""
Intent classifier for the AI Python Tutor.
Uses keyword heuristics + pattern matching to classify user messages.
Falls back gracefully so ambiguous messages still get a helpful response.
"""

import re

# ---------------------------------------------------------------------------
# Keyword bank — broad and natural-language-aware
# ---------------------------------------------------------------------------

INTENT_KEYWORDS: dict[str, list[str]] = {
    "concept": [
        # Direct requests
        "explain", "what is", "what are", "what's", "whats",
        "how does", "how do", "how does", "how can", "how would",
        "teach me", "teach", "tell me about", "tell me how",
        "define", "definition", "meaning of", "what does",
        "understand", "help me understand", "i don't understand",
        "i dont understand", "confused about", "confused by",
        "describe", "overview", "introduction to", "basics of",
        "difference between", "vs ", " vs", "versus",
        "when to use", "why use", "why do we", "what happens when",
        "how is", "what happens", "can you explain", "could you explain",
        "show me", "walk me through", "break down",
        # Topics people just name directly
        "decorator", "generator", "iterator", "comprehension",
        "lambda", "closure", "scope", "namespace", "recursion",
        "inheritance", "polymorphism", "encapsulation", "abstraction",
        "async", "await", "coroutine", "threading", "multiprocessing",
        "metaclass", "descriptor", "context manager", "with statement",
        "type hint", "type annotation", "dataclass", "namedtuple",
        "unpacking", "packing", "args", "kwargs", "f-string",
        "slice", "slicing", "indexing", "mutable", "immutable",
        "shallow copy", "deep copy", "garbage collection",
        "gil", "global interpreter lock",
        "syntax", "comment", "casting", "boolean", "operator",
        "string method", "string format", "f-string", "escape character",
        "list method", "list comprehension", "tuple", "set", "dictionary",
        "dict method", "set method", "break", "continue", "pass",
        "arguments", "parameters", "return value",
        "regular expression", "regex",
        "math module", "datetime", "json", "random", "os module",
        "file read", "file write", "file delete",
        "custom exception", "try except", "finally",
        "numpy", "pandas", "matplotlib", "dataframe",
        "linked list", "stack", "queue", "hash table", "binary tree",
        "graph", "sorting algorithm", "searching algorithm",
        "prompt engineering", "ai integration",
        "match statement", "range", "array", "iterator",
        "date", "pip", "none", "user input", "virtual environment",
        "self parameter", "class property", "class method", "inner class",
        "read file", "write file", "delete file",
        "scipy", "django", "flask", "fastapi",
        "bubble sort", "selection sort", "insertion sort",
        "quick sort", "merge sort", "counting sort", "radix sort",
        "binary search", "linear search",
        "avl tree", "binary search tree",
        "mysql", "mongodb", "database",
        "built-in function", "keyword", "glossary",
        "requests module", "statistics module", "cmath",
    ],
    "debug": [
        # Error types
        "error", "exception", "traceback", "stack trace",
        "syntaxerror", "typeerror", "valueerror", "nameerror",
        "indexerror", "keyerror", "attributeerror", "importerror",
        "runtimeerror", "zerodivisionerror", "filenotfounderror",
        "stopiteration", "overflowerror", "memoryerror",
        "recursionerror", "indentationerror", "unicodeerror",
        # Problem descriptions
        "not working", "doesn't work", "doesnt work", "won't work",
        "wont work", "bug", "fix", "broken", "crash", "crashes",
        "fails", "failing", "failed", "wrong output", "wrong result",
        "unexpected", "incorrect", "not getting", "getting wrong",
        "issue", "problem with my code", "help with my code",
        "what's wrong", "whats wrong", "why is this", "why does this",
        "why isn't", "why isnt", "can't run", "cant run",
        "not printing", "not returning", "not working as expected",
        "debug", "why is my",
    ],
    "codegen": [
        # Direct code requests
        "write", "generate", "create", "build", "implement",
        "make a", "make me", "make an", "code for", "code that",
        "give me code", "show me code", "write code", "write a",
        "write an", "write me", "can you write", "could you write",
        "i need code", "i need a", "i need to", "help me write",
        "show me how to code", "show me how to write",
        "program that", "script that", "script to", "function that",
        "function to", "class that", "class to", "method that",
        "snippet", "example of", "sample code", "boilerplate",
        "template", "how to implement", "how to create", "how to build",
        "how to make", "how to write a", "how to write an",
        "demonstrate", "show an example",
    ],
    "exercise": [
        "exercise", "practice", "challenge", "quiz me", "test me",
        "problem", "task", "assignment", "drill",
        "test my knowledge", "test my understanding",
        "give me a problem", "give me an exercise", "give me a challenge",
        "let me try", "let me practice", "i want to practice",
        "i want to try", "something to practice",
        "project idea", "project for", "coding challenge",
        "assess", "check my understanding",
    ],
}

# ---------------------------------------------------------------------------
# Regex patterns for natural phrasing the keyword list misses
# ---------------------------------------------------------------------------

_CONCEPT_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bwhat\b.{0,20}\bpython\b",
        r"\bhow\b.{0,30}\bwork",
        r"\bcan you.{0,20}\bexplain\b",
        r"\bi.{0,10}(confused|lost|stuck).{0,30}\b(about|with|on)\b",
        r"\bwhat.{0,10}(mean|means|meant)\b",
        r"\b(difference|diff)\b.{0,20}\bbetween\b",
        r"\bwhen.{0,20}\buse\b",
        r"\bwhy.{0,20}\b(use|need|have)\b",
        r"\bhow.{0,20}\b(work|works|used|use)\b",
    ]
]

_DEBUG_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bwhy.{0,30}(isn.t|isnt|doesn.t|doesnt|wont|won.t|not working|not|never)\b",
        r"\bwhy.{0,20}(loop|function|code|script|program).{0,20}(run|work|stop|return|print)\b",
        r"\b(getting|got|seeing)\b.{0,20}\berror\b",
        r"\bmy.{0,30}\b(code|program|script|function)\b.{0,20}\b(not|doesn.t|wont)\b",
        r"```python",
        r"```\s*\n",
    ]
]

_CODEGEN_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bhow (do|can|would|to)\b.{0,30}\b(code|write|implement|create|build|make)\b",
        r"\b(show|give).{0,10}me.{0,20}\b(example|code|snippet)\b",
    ]
]


# ---------------------------------------------------------------------------
# Public classifier
# ---------------------------------------------------------------------------

def classify_intent(message: str) -> str:
    """
    Classify the intent of a user message.

    Returns one of: 'concept', 'debug', 'codegen', 'exercise', 'general'

    'general' replaces the old 'ambiguous' — it maps to a helpful catch-all
    prompt that still teaches rather than stonewalling with a clarifying question.
    """
    if not message or not message.strip():
        return "general"

    lowered = message.lower()

    # ── Keyword scoring ──────────────────────────────────────────────────────
    scores: dict[str, int] = {intent: 0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[intent] += 1

    # ── Pattern bonus ────────────────────────────────────────────────────────
    for pat in _CONCEPT_PATTERNS:
        if pat.search(message):
            scores["concept"] += 2

    for pat in _DEBUG_PATTERNS:
        if pat.search(message):
            scores["debug"] += 2

    for pat in _CODEGEN_PATTERNS:
        if pat.search(message):
            scores["codegen"] += 2

    # ── Pick winner ──────────────────────────────────────────────────────────
    best_intent = max(scores, key=lambda k: scores[k])
    best_score  = scores[best_intent]

    # Even with score 0, default to 'concept' for short Python-topic messages
    # rather than stonewalling with a clarifying question
    if best_score == 0:
        # Check if it looks like a Python term / greeting / general question
        # → treat as concept request so the model still helps
        return "general"

    return best_intent
