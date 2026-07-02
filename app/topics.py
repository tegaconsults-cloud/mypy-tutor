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

    # ── NumPy ─────────────────────────────────────────────────────────────────
    "NumPy Intro",
    "NumPy Getting Started",
    "NumPy Creating Arrays",
    "NumPy Array Indexing",
    "NumPy Array Slicing",
    "NumPy Data Types",
    "NumPy Copy vs View",
    "NumPy Array Shape",
    "NumPy Array Reshape",
    "NumPy Array Iterating",
    "NumPy Array Join",
    "NumPy Array Split",
    "NumPy Array Search",
    "NumPy Array Sort",
    "NumPy Array Filter",
    # NumPy Random
    "NumPy Random Intro",
    "NumPy Data Distribution",
    "NumPy Random Permutation",
    "NumPy Seaborn Module",
    "NumPy Normal Distribution",
    "NumPy Binomial Distribution",
    "NumPy Poisson Distribution",
    "NumPy Uniform Distribution",
    "NumPy Logistic Distribution",
    "NumPy Multinomial Distribution",
    "NumPy Exponential Distribution",
    "NumPy Chi Square Distribution",
    "NumPy Rayleigh Distribution",
    "NumPy Pareto Distribution",
    "NumPy Zipf Distribution",
    # NumPy ufunc
    "NumPy ufunc Intro",
    "NumPy ufunc Create Function",
    "NumPy ufunc Simple Arithmetic",
    "NumPy ufunc Rounding Decimals",
    "NumPy ufunc Logs",
    "NumPy ufunc Summations",
    "NumPy ufunc Products",
    "NumPy ufunc Differences",
    "NumPy ufunc Finding LCM",
    "NumPy ufunc Finding GCD",
    "NumPy ufunc Trigonometric",
    "NumPy ufunc Hyperbolic",
    "NumPy ufunc Set Operations",

    # ── Pandas ────────────────────────────────────────────────────────────────
    "Pandas Intro",
    "Pandas Getting Started",
    "Pandas Series",
    "Pandas DataFrames",
    "Pandas Read CSV",
    "Pandas Read JSON",
    "Pandas Analyzing Data",
    "Pandas Cleaning Data",
    "Pandas Cleaning Empty Cells",
    "Pandas Cleaning Wrong Format",
    "Pandas Cleaning Wrong Data",
    "Pandas Removing Duplicates",
    "Pandas Correlations",
    "Pandas Plotting",

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
