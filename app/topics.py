"""
Complete Python topic list — mirrors the full W3Schools Python curriculum.
Every topic a learner can ask about, get quizzed on, and have tracked.
"""

SUPPORTED_TOPICS: list[str] = [

    # ── Python Basics ────────────────────────────────────────────────────────
    "Python Intro",
    "Python Get Started",
    "Python Syntax",
    "Python Output",
    "Python Comments",
    "Python Variables",
    "Python Data Types",
    "Python Numbers",
    "Python Casting",
    "Python Strings",
    "Python Booleans",
    "Python Operators",

    # ── String Details ───────────────────────────────────────────────────────
    "String Methods",
    "String Formatting",
    "String Slicing",

    # ── Collections ──────────────────────────────────────────────────────────
    "Python Lists",
    "List Methods",
    "List Comprehension",
    "Python Tuples",
    "Tuple Methods",
    "Python Sets",
    "Set Methods",
    "Python Dictionaries",
    "Dictionary Methods",

    # ── Control Flow ─────────────────────────────────────────────────────────
    "If Else",
    "Match Statement",
    "While Loops",
    "For Loops",
    "Python Range",
    "Break and Continue",
    "Pass Statement",

    # ── Functions ────────────────────────────────────────────────────────────
    "Python Functions",
    "Function Arguments",
    "Lambda Functions",
    "Python Scope",
    "Python Closures",
    "Python Recursion",
    "Python Decorators",

    # ── Arrays & Iterators ───────────────────────────────────────────────────
    "Python Arrays",
    "Python Iterators",
    "Python Generators",

    # ── Modules ──────────────────────────────────────────────────────────────
    "Python Modules",
    "Python Dates",
    "Python Math",
    "Python JSON",
    "Python RegEx",
    "Python PIP",
    "Python Random Module",
    "Requests Module",
    "Statistics Module",
    "cMath Module",

    # ── Error Handling ───────────────────────────────────────────────────────
    "Try Except",
    "Custom Exceptions",

    # ── I/O ──────────────────────────────────────────────────────────────────
    "Python None",
    "User Input",
    "Virtual Environments",

    # ── OOP ──────────────────────────────────────────────────────────────────
    "Python OOP",
    "Classes and Objects",
    "__init__ Method",
    "Self Parameter",
    "Class Properties",
    "Class Methods",
    "Python Inheritance",
    "Python Polymorphism",
    "Python Encapsulation",
    "Inner Classes",

    # ── File Handling ────────────────────────────────────────────────────────
    "File Handling",
    "Read Files",
    "Write Files",
    "Delete Files",
    "File Methods",

    # ── Data Science Libraries ───────────────────────────────────────────────
    "NumPy",
    "Pandas",
    "SciPy",
    "Django",
    "Matplotlib",
    "Matplotlib Pyplot",
    "Matplotlib Plotting",
    "Matplotlib Markers",
    "Matplotlib Labels",
    "Matplotlib Subplots",
    "Matplotlib Scatter",
    "Matplotlib Bar Charts",
    "Matplotlib Histograms",
    "Matplotlib Pie Charts",

    # ── DSA ──────────────────────────────────────────────────────────────────
    "DSA Intro",
    "Lists and Arrays",
    "Stacks",
    "Queues",
    "Linked Lists",
    "Hash Tables",
    "Trees",
    "Binary Trees",
    "Binary Search Trees",
    "AVL Trees",
    "Graphs",
    "Linear Search",
    "Binary Search",
    "Bubble Sort",
    "Selection Sort",
    "Insertion Sort",
    "Quick Sort",
    "Counting Sort",
    "Radix Sort",
    "Merge Sort",

    # ── Databases ────────────────────────────────────────────────────────────
    "MySQL",
    "MySQL Create Database",
    "MySQL Create Table",
    "MySQL Insert",
    "MySQL Select",
    "MySQL Where",
    "MySQL Order By",
    "MySQL Delete",
    "MySQL Update",
    "MySQL Join",
    "MongoDB",
    "MongoDB Insert",
    "MongoDB Find",
    "MongoDB Query",
    "MongoDB Update",
    "MongoDB Delete",

    # ── Reference & Advanced ─────────────────────────────────────────────────
    "Built-in Functions",
    "Python Keywords",
    "Python Exceptions",
    "Python Glossary",
    "Type Hints",
    "Dataclasses",
    "Context Managers",
    "Args and Kwargs",
    "Unpacking",
    "Threading",
    "Multiprocessing",
    "Async Await",
    "Shallow and Deep Copy",

    # ── Flask / FastAPI / APIs ────────────────────────────────────────────────
    "Flask",
    "FastAPI",
    "REST APIs",

    # ── Prompt Engineering & AI ──────────────────────────────────────────────
    "Prompt Engineering",
    "AI Integration",
]


def get_topics() -> list[str]:
    """Return the full list of supported Python topics."""
    return SUPPORTED_TOPICS
