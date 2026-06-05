"""
Intent classifier for the AI Python Tutor.
Uses keyword-based heuristics to classify user messages into one of five intents.
"""

INTENT_KEYWORDS: dict[str, list[str]] = {
    "concept": [
        "explain", "what is", "what are", "how does", "how do", "teach me",
        "define", "definition", "understand", "meaning of", "tell me about",
        "describe", "overview", "introduction to", "basics of",
    ],
    "debug": [
        "error", "exception", "traceback", "not working", "bug", "fix",
        "broken", "crash", "fails", "failing", "wrong output", "unexpected",
        "syntaxerror", "typeerror", "valueerror", "nameerror", "indexerror",
        "attributeerror", "keyerror", "importerror", "runtimeerror",
    ],
    "codegen": [
        "write", "generate", "create", "build", "code for", "implement",
        "make a", "make me", "give me code", "show me how to code",
        "program that", "script that", "function that", "class that",
    ],
    "exercise": [
        "exercise", "practice", "challenge", "quiz", "problem", "task",
        "assignment", "drill", "test my", "give me a problem", "let me try",
    ],
}


def classify_intent(message: str) -> str:
    """
    Classify the intent of a user message using keyword heuristics.

    Returns one of: 'concept', 'debug', 'codegen', 'exercise', 'ambiguous'
    """
    if not message or not message.strip():
        return "ambiguous"

    lowered = message.lower()

    scores: dict[str, int] = {intent: 0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[intent] += 1

    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    if best_score == 0:
        return "ambiguous"

    return best_intent
