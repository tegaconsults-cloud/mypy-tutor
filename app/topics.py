SUPPORTED_TOPICS: list[str] = [
    "variables",
    "data types",
    "loops",
    "functions",
    "OOP",
    "file handling",
    "exception handling",
    "modules",
    "APIs",
    "data structures",
    "algorithms",
    "Flask basics",
    "FastAPI basics",
]


def get_topics() -> list[str]:
    """Return the list of all supported Python topics."""
    return SUPPORTED_TOPICS
