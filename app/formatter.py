"""
Response formatter — topic detection aligned with full W3Schools Python curriculum.
"""

import re
from app.topics import SUPPORTED_TOPICS

# ---------------------------------------------------------------------------
# Alias map: keyword/phrase → canonical topic name (specific before generic)
# ---------------------------------------------------------------------------
_TOPIC_ALIASES: list[tuple[str, str]] = [
    # Prompt / AI (before "api")
    ("prompt engineering",   "Prompt Engineering"),
    ("ai integration",       "AI Integration"),
    ("openai",               "AI Integration"),
    ("llm",                  "AI Integration"),
    # Web frameworks (before bare "api")
    ("fastapi",              "FastAPI"),
    ("flask",                "Flask"),
    ("django",               "Django"),
    # DSA sorts (before generic "sort")
    ("bubble sort",          "Bubble Sort"),
    ("selection sort",       "Selection Sort"),
    ("insertion sort",       "Insertion Sort"),
    ("quick sort",           "Quick Sort"),
    ("counting sort",        "Counting Sort"),
    ("radix sort",           "Radix Sort"),
    ("merge sort",           "Merge Sort"),
    # DSA searches
    ("binary search tree",   "Binary Search Trees"),
    ("avl tree",             "AVL Trees"),
    ("binary tree",          "Binary Trees"),
    ("binary search",        "Binary Search"),
    ("linear search",        "Linear Search"),
    # DSA structures
    ("linked list",          "Linked Lists"),
    ("hash table",           "Hash Tables"),
    ("hash map",             "Hash Tables"),
    ("graph",                "Graphs"),
    ("tree",                 "Trees"),
    ("stack",                "Stacks"),
    ("queue",                "Queues"),
    # Matplotlib
    ("plt.scatter",          "Matplotlib Scatter"),
    ("plt.bar",              "Matplotlib Bar Charts"),
    ("plt.hist",             "Matplotlib Histograms"),
    ("plt.pie",              "Matplotlib Pie Charts"),
    ("plt.subplot",          "Matplotlib Subplots"),
    ("plt.plot",             "Matplotlib Plotting"),
    ("matplotlib",           "Matplotlib"),
    ("pyplot",               "Matplotlib Pyplot"),
    # Data science
    ("scipy",                "SciPy"),
    ("numpy",                "NumPy"),
    ("np.",                  "NumPy"),
    ("pandas",               "Pandas"),
    ("dataframe",            "Pandas"),
    ("pd.",                  "Pandas"),
    # MySQL
    ("mysql",                "MySQL"),
    ("create table",         "MySQL Create Table"),
    ("create database",      "MySQL Create Database"),
    # MongoDB
    ("mongodb",              "MongoDB"),
    ("pymongo",              "MongoDB"),
    # Async
    ("asyncio",              "Async Await"),
    ("async def",            "Async Await"),
    ("await",                "Async Await"),
    ("coroutine",            "Async Await"),
    ("threading",            "Threading"),
    ("multiprocessing",      "Multiprocessing"),
    # Advanced
    ("dataclass",            "Dataclasses"),
    ("@dataclass",           "Dataclasses"),
    ("context manager",      "Context Managers"),
    ("__enter__",            "Context Managers"),
    ("with open",            "Context Managers"),
    ("shallow copy",         "Shallow and Deep Copy"),
    ("deep copy",            "Shallow and Deep Copy"),
    ("type hint",            "Type Hints"),
    ("type annotation",      "Type Hints"),
    ("*args",                "Args and Kwargs"),
    ("**kwargs",             "Args and Kwargs"),
    ("unpack",               "Unpacking"),
    # OOP
    ("magic method",         "Class Methods"),
    ("dunder",               "Class Methods"),
    ("__init__",             "__init__ Method"),
    ("__str__",              "Class Methods"),
    ("__repr__",             "Class Methods"),
    ("polymorphism",         "Python Polymorphism"),
    ("encapsulation",        "Python Encapsulation"),
    ("abstraction",          "Python OOP"),
    ("inner class",          "Inner Classes"),
    ("inheritance",          "Python Inheritance"),
    ("subclass",             "Python Inheritance"),
    ("super()",              "Python Inheritance"),
    ("class ",               "Classes and Objects"),
    ("self",                 "Self Parameter"),
    # Iterators / generators
    ("generator",            "Python Generators"),
    ("yield",                "Python Generators"),
    ("iterator",             "Python Iterators"),
    ("__iter__",             "Python Iterators"),
    ("__next__",             "Python Iterators"),
    # Decorators / closures / lambda
    ("decorator",            "Python Decorators"),
    ("@property",            "Python Decorators"),
    ("closure",              "Python Closures"),
    ("lambda",               "Lambda Functions"),
    ("list comprehension",   "List Comprehension"),
    ("comprehension",        "List Comprehension"),
    # Scope
    ("global ",              "Python Scope"),
    ("nonlocal",             "Python Scope"),
    ("scope",                "Python Scope"),
    ("namespace",            "Python Scope"),
    # Modules
    ("import math",          "Python Math"),
    ("math.",                "Python Math"),
    ("import datetime",      "Python Dates"),
    ("datetime",             "Python Dates"),
    ("import json",          "Python JSON"),
    ("json.",                "Python JSON"),
    ("regex",                "Python RegEx"),
    ("re.",                  "Python RegEx"),
    ("regular expression",   "Python RegEx"),
    ("import random",        "Python Random Module"),
    ("random.",              "Python Random Module"),
    ("import requests",      "Requests Module"),
    ("requests.",            "Requests Module"),
    ("statistics.",          "Statistics Module"),
    ("cmath",                "cMath Module"),
    ("pip install",          "Python PIP"),
    ("virtualenv",           "Virtual Environments"),
    ("venv",                 "Virtual Environments"),
    ("import ",              "Python Modules"),
    ("module",               "Python Modules"),
    ("package",              "Python Modules"),
    # File handling
    ("os.remove",            "Delete Files"),
    ("os.unlink",            "Delete Files"),
    ("open(",                "File Handling"),
    (".read(",               "Read Files"),
    ("readlines",            "Read Files"),
    (".write(",              "Write Files"),
    # Exceptions
    ("custom exception",     "Custom Exceptions"),
    ("raise ",               "Custom Exceptions"),
    ("try:",                 "Try Except"),
    ("except ",              "Try Except"),
    ("finally",              "Try Except"),
    ("exception",            "Python Exceptions"),
    # I/O
    ("input(",               "User Input"),
    ("none",                 "Python None"),
    # Collections
    ("dict",                 "Python Dictionaries"),
    ("dictionary",           "Python Dictionaries"),
    (".append(",             "List Methods"),
    (".sort(",               "List Methods"),
    (".pop(",                "List Methods"),
    ("set(",                 "Python Sets"),
    ("frozenset",            "Python Sets"),
    ("tuple",                "Python Tuples"),
    ("list",                 "Python Lists"),
    ("array",                "Python Arrays"),
    # Control flow
    ("match ",               "Match Statement"),
    ("for loop",             "For Loops"),
    ("for ",                 "For Loops"),
    ("while loop",           "While Loops"),
    ("while ",               "While Loops"),
    ("break",                "Break and Continue"),
    ("continue",             "Break and Continue"),
    ("pass",                 "Pass Statement"),
    ("range(",               "Python Range"),
    ("if ",                  "If Else"),
    ("elif",                 "If Else"),
    # Functions
    ("def ",                 "Python Functions"),
    ("function",             "Python Functions"),
    ("return",               "Python Functions"),
    ("argument",             "Function Arguments"),
    ("parameter",            "Function Arguments"),
    ("recursion",            "Python Recursion"),
    # Strings
    ("f\"",                  "String Formatting"),
    ("f'",                   "String Formatting"),
    ("format()",             "String Formatting"),
    (".upper(",              "String Methods"),
    (".lower(",              "String Methods"),
    (".strip(",              "String Methods"),
    (".split(",              "String Methods"),
    (".replace(",            "String Methods"),
    ("[:",                   "String Slicing"),
    ("string",               "Python Strings"),
    ("str(",                 "Python Strings"),
    # Basics
    ("boolean",              "Python Booleans"),
    ("true",                 "Python Booleans"),
    ("false",                "Python Booleans"),
    ("int(",                 "Python Casting"),
    ("float(",               "Python Casting"),
    ("cast",                 "Python Casting"),
    ("operator",             "Python Operators"),
    ("arithmetic",           "Python Operators"),
    ("comment",              "Python Comments"),
    ("variable",             "Python Variables"),
    ("data type",            "Python Data Types"),
    ("number",               "Python Numbers"),
    ("integer",              "Python Numbers"),
    ("syntax",               "Python Syntax"),
    ("print(",               "Python Output"),
    ("keyword",              "Python Keywords"),
    ("built-in function",    "Built-in Functions"),
    ("api",                  "REST APIs"),
]

# Sorted topic patterns (longest first for exact matching)
_SORTED_TOPIC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\b' + re.escape(t) + r'\b', re.IGNORECASE), t)
    for t in sorted(SUPPORTED_TOPICS, key=len, reverse=True)
]


def _detect_topic(content: str) -> str | None:
    """Detect canonical topic from message or response text."""
    lowered = content.lower()
    for pattern, canonical in _SORTED_TOPIC_PATTERNS:
        if pattern.search(content):
            return canonical
    for alias, canonical in _TOPIC_ALIASES:
        if alias in lowered:
            return canonical
    return None


def format_response(content: str, intent: str) -> dict:
    topic = _detect_topic(content)
    return {"intent": intent, "content": content, "topic": topic}
