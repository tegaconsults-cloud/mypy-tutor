"""
Structured Python courses — full W3Schools curriculum coverage.
9 courses spanning beginner to advanced.
"""

from app.models import Course, CourseStep

COURSES: dict[str, Course] = {

    # ─────────────────────────────────────────────────────────────────────────
    # BEGINNER
    # ─────────────────────────────────────────────────────────────────────────

    "python-fundamentals": Course(
        name="python-fundamentals",
        level="beginner",
        description="Master Python from zero — syntax, variables, data types, operators, and output.",
        steps=[
            CourseStep(step=1,  title="Python Intro & Get Started",  description="What Python is and how to install it.", intent="concept"),
            CourseStep(step=2,  title="Python Syntax",               description="Indentation, statements, and structure.", intent="concept"),
            CourseStep(step=3,  title="Python Output",               description="Using print() and output formatting.", intent="concept"),
            CourseStep(step=4,  title="Python Comments",             description="Single-line and multi-line comments.", intent="concept"),
            CourseStep(step=5,  title="Python Variables",            description="Declaring, assigning, and naming variables.", intent="concept"),
            CourseStep(step=6,  title="Variables Exercise",          description="Practice declaring and using variables.", intent="exercise"),
            CourseStep(step=7,  title="Python Data Types",           description="int, float, str, bool, list, dict, etc.", intent="concept"),
            CourseStep(step=8,  title="Python Numbers",              description="Integers, floats, and complex numbers.", intent="concept"),
            CourseStep(step=9,  title="Python Casting",              description="Converting between types with int(), str(), float().", intent="concept"),
            CourseStep(step=10, title="Python Booleans",             description="True, False, and boolean logic.", intent="concept"),
            CourseStep(step=11, title="Python Operators",            description="Arithmetic, comparison, logical, and assignment operators.", intent="concept"),
            CourseStep(step=12, title="Operators Exercise",          description="Solve problems using Python operators.", intent="exercise"),
            CourseStep(step=13, title="Basics Quiz",                 description="Test your Python basics knowledge.", intent="quiz"),
            CourseStep(step=14, title="Capstone Project",            description="Build a simple calculator using variables and operators.", intent="codegen"),
        ],
    ),

    "python-strings": Course(
        name="python-strings",
        level="beginner",
        description="Master Python strings — methods, formatting, slicing, and f-strings.",
        steps=[
            CourseStep(step=1,  title="Python Strings",              description="Creating and accessing strings.", intent="concept"),
            CourseStep(step=2,  title="String Slicing",              description="Slice and index strings with [ : ].", intent="concept"),
            CourseStep(step=3,  title="String Slicing Exercise",     description="Practice slicing strings.", intent="exercise"),
            CourseStep(step=4,  title="String Methods",              description="upper, lower, strip, split, replace, find, count and more.", intent="concept"),
            CourseStep(step=5,  title="String Methods Exercise",     description="Use the most common string methods.", intent="exercise"),
            CourseStep(step=6,  title="String Formatting",           description="f-strings, format(), and % formatting.", intent="concept"),
            CourseStep(step=7,  title="String Formatting Exercise",  description="Build formatted output strings.", intent="exercise"),
            CourseStep(step=8,  title="Strings Quiz",                description="Test your string knowledge.", intent="quiz"),
        ],
    ),

    "python-collections": Course(
        name="python-collections",
        level="beginner",
        description="Python Lists, Tuples, Sets, and Dictionaries — the four core collection types.",
        steps=[
            CourseStep(step=1,  title="Python Lists",                description="Creating, accessing, and modifying lists.", intent="concept"),
            CourseStep(step=2,  title="List Methods",                description="append, remove, sort, pop, insert and more.", intent="concept"),
            CourseStep(step=3,  title="List Comprehension",          description="Create lists with one-line expressions.", intent="concept"),
            CourseStep(step=4,  title="Lists Exercise",              description="Manipulate lists with methods and comprehensions.", intent="exercise"),
            CourseStep(step=5,  title="Python Tuples",               description="Immutable sequences and tuple methods.", intent="concept"),
            CourseStep(step=6,  title="Python Sets",                 description="Unordered unique collections and set methods.", intent="concept"),
            CourseStep(step=7,  title="Python Dictionaries",         description="Key-value storage and dictionary methods.", intent="concept"),
            CourseStep(step=8,  title="Dictionary Methods",          description="keys, values, items, get, update and more.", intent="concept"),
            CourseStep(step=9,  title="Collections Exercise",        description="Build a word frequency counter using a dictionary.", intent="exercise"),
            CourseStep(step=10, title="Collections Quiz",            description="Test your knowledge of Python collections.", intent="quiz"),
            CourseStep(step=11, title="Capstone Project",            description="Build a student grade tracker using lists and dictionaries.", intent="codegen"),
        ],
    ),

    "python-control-flow": Course(
        name="python-control-flow",
        level="beginner",
        description="If/Else, Match, While, For, Range, Break, Continue — full control flow.",
        steps=[
            CourseStep(step=1,  title="If...Else",                   description="Conditional statements with if, elif, else.", intent="concept"),
            CourseStep(step=2,  title="Match Statement",             description="Python 3.10+ structural pattern matching.", intent="concept"),
            CourseStep(step=3,  title="While Loops",                 description="Repeating code while a condition is true.", intent="concept"),
            CourseStep(step=4,  title="For Loops",                   description="Iterating over sequences with for.", intent="concept"),
            CourseStep(step=5,  title="Python Range",                description="Generating number sequences with range().", intent="concept"),
            CourseStep(step=6,  title="Break and Continue",          description="Controlling loop flow with break and continue.", intent="concept"),
            CourseStep(step=7,  title="Pass Statement",              description="Using pass as a placeholder.", intent="concept"),
            CourseStep(step=8,  title="Control Flow Exercise",       description="Write programs using loops and conditionals.", intent="exercise"),
            CourseStep(step=9,  title="Control Flow Quiz",           description="Test your control flow knowledge.", intent="quiz"),
            CourseStep(step=10, title="Capstone Project",            description="Build a number guessing game.", intent="codegen"),
        ],
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # INTERMEDIATE
    # ─────────────────────────────────────────────────────────────────────────

    "python-functions-advanced": Course(
        name="python-functions-advanced",
        level="intermediate",
        description="Functions, Lambda, Scope, Closures, Decorators, Iterators, and Generators.",
        steps=[
            CourseStep(step=1,  title="Python Functions",            description="Defining, calling, and returning from functions.", intent="concept"),
            CourseStep(step=2,  title="Function Arguments",          description="Positional, keyword, *args, and **kwargs.", intent="concept"),
            CourseStep(step=3,  title="Arguments Exercise",          description="Write flexible functions with *args/**kwargs.", intent="exercise"),
            CourseStep(step=4,  title="Lambda Functions",            description="Anonymous one-line functions.", intent="concept"),
            CourseStep(step=5,  title="Python Scope",                description="Local, global, and nonlocal scope.", intent="concept"),
            CourseStep(step=6,  title="Python Recursion",            description="Functions that call themselves.", intent="concept"),
            CourseStep(step=7,  title="Python Closures",             description="Functions that capture their environment.", intent="concept"),
            CourseStep(step=8,  title="Python Decorators",           description="Wrapping functions with @decorator syntax.", intent="concept"),
            CourseStep(step=9,  title="Decorators Exercise",         description="Write and apply a custom decorator.", intent="exercise"),
            CourseStep(step=10, title="Python Arrays",               description="Using arrays vs lists in Python.", intent="concept"),
            CourseStep(step=11, title="Python Iterators",            description="__iter__ and __next__ explained.", intent="concept"),
            CourseStep(step=12, title="Python Generators",           description="yield and lazy evaluation.", intent="concept"),
            CourseStep(step=13, title="Advanced Functions Quiz",     description="Test your advanced functions knowledge.", intent="quiz"),
            CourseStep(step=14, title="Capstone Project",            description="Build a data pipeline using generators and decorators.", intent="codegen"),
        ],
    ),

    "python-oop": Course(
        name="python-oop",
        level="intermediate",
        description="Object-Oriented Python — Classes, Inheritance, Polymorphism, Encapsulation.",
        steps=[
            CourseStep(step=1,  title="Python OOP Intro",            description="What OOP is and why it matters.", intent="concept"),
            CourseStep(step=2,  title="Classes and Objects",         description="Creating classes and instantiating objects.", intent="concept"),
            CourseStep(step=3,  title="__init__ Method",             description="Constructors and instance variables.", intent="concept"),
            CourseStep(step=4,  title="Self Parameter",              description="How self references the instance.", intent="concept"),
            CourseStep(step=5,  title="Class Properties",            description="Instance and class attributes.", intent="concept"),
            CourseStep(step=6,  title="Class Methods",               description="Instance, class, and static methods.", intent="concept"),
            CourseStep(step=7,  title="OOP Exercise",                description="Build a complete class from scratch.", intent="exercise"),
            CourseStep(step=8,  title="Python Inheritance",          description="Subclasses and method overriding.", intent="concept"),
            CourseStep(step=9,  title="Inheritance Exercise",        description="Extend a base class.", intent="exercise"),
            CourseStep(step=10, title="Python Polymorphism",         description="Same interface, different implementations.", intent="concept"),
            CourseStep(step=11, title="Python Encapsulation",        description="Private and protected attributes.", intent="concept"),
            CourseStep(step=12, title="Inner Classes",               description="Classes defined inside other classes.", intent="concept"),
            CourseStep(step=13, title="OOP Quiz",                    description="Test your OOP knowledge.", intent="quiz"),
            CourseStep(step=14, title="Capstone Project",            description="Build a bank account class hierarchy.", intent="codegen"),
        ],
    ),

    "python-modules-stdlib": Course(
        name="python-modules-stdlib",
        level="intermediate",
        description="Python standard library — Dates, Math, JSON, RegEx, PIP, File Handling.",
        steps=[
            CourseStep(step=1,  title="Python Modules",              description="Creating, importing, and using modules.", intent="concept"),
            CourseStep(step=2,  title="Python Dates",                description="datetime module — dates, times, and formatting.", intent="concept"),
            CourseStep(step=3,  title="Dates Exercise",              description="Format and calculate dates.", intent="exercise"),
            CourseStep(step=4,  title="Python Math",                 description="math module — functions and constants.", intent="concept"),
            CourseStep(step=5,  title="Python JSON",                 description="Parsing and generating JSON data.", intent="concept"),
            CourseStep(step=6,  title="JSON Exercise",               description="Serialize and deserialize data structures.", intent="exercise"),
            CourseStep(step=7,  title="Python RegEx",                description="Pattern matching with the re module.", intent="concept"),
            CourseStep(step=8,  title="RegEx Exercise",              description="Write regex patterns for real tasks.", intent="exercise"),
            CourseStep(step=9,  title="Python PIP",                  description="Installing and managing packages.", intent="concept"),
            CourseStep(step=10, title="Virtual Environments",        description="Creating isolated Python environments.", intent="concept"),
            CourseStep(step=11, title="Try Except",                  description="Handling errors with try/except/finally.", intent="concept"),
            CourseStep(step=12, title="Custom Exceptions",           description="Defining your own exception classes.", intent="concept"),
            CourseStep(step=13, title="File Handling",               description="Opening, reading, writing, and deleting files.", intent="concept"),
            CourseStep(step=14, title="File Handling Exercise",      description="Build a file-based note manager.", intent="exercise"),
            CourseStep(step=15, title="Modules Quiz",                description="Test your standard library knowledge.", intent="quiz"),
        ],
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # ADVANCED
    # ─────────────────────────────────────────────────────────────────────────

    "python-dsa": Course(
        name="python-dsa",
        level="advanced",
        description="Data Structures and Algorithms — DSA from W3Schools, fully in Python.",
        steps=[
            CourseStep(step=1,  title="DSA Intro",                   description="What DSA is and why it matters.", intent="concept"),
            CourseStep(step=2,  title="Lists and Arrays",            description="Arrays vs lists, time complexity.", intent="concept"),
            CourseStep(step=3,  title="Stacks",                      description="LIFO structure with push/pop.", intent="concept"),
            CourseStep(step=4,  title="Queues",                      description="FIFO structure with enqueue/dequeue.", intent="concept"),
            CourseStep(step=5,  title="Linked Lists",                description="Singly and doubly linked lists.", intent="concept"),
            CourseStep(step=6,  title="Hash Tables",                 description="Key-value storage with hashing.", intent="concept"),
            CourseStep(step=7,  title="Trees",                       description="Tree structure, nodes, and traversal.", intent="concept"),
            CourseStep(step=8,  title="Binary Trees",                description="Binary tree operations.", intent="concept"),
            CourseStep(step=9,  title="Binary Search Trees",         description="BST insert, search, delete.", intent="concept"),
            CourseStep(step=10, title="AVL Trees",                   description="Self-balancing BST.", intent="concept"),
            CourseStep(step=11, title="Graphs",                      description="Graph representation, BFS, DFS.", intent="concept"),
            CourseStep(step=12, title="Linear Search",               description="Sequential search algorithm.", intent="concept"),
            CourseStep(step=13, title="Binary Search",               description="Divide-and-conquer search.", intent="concept"),
            CourseStep(step=14, title="Bubble Sort",                 description="Simple comparison-based sort.", intent="concept"),
            CourseStep(step=15, title="Selection Sort",              description="Find minimum and place.", intent="concept"),
            CourseStep(step=16, title="Insertion Sort",              description="Build sorted array one item at a time.", intent="concept"),
            CourseStep(step=17, title="Quick Sort",                  description="Partition-based recursive sort.", intent="concept"),
            CourseStep(step=18, title="Merge Sort",                  description="Divide, sort, and merge.", intent="concept"),
            CourseStep(step=19, title="Counting & Radix Sort",       description="Non-comparison sorting algorithms.", intent="concept"),
            CourseStep(step=20, title="DSA Quiz",                    description="Test your DSA knowledge.", intent="quiz"),
            CourseStep(step=21, title="Capstone Project",            description="Implement a graph BFS/DFS pathfinder in Python.", intent="codegen"),
        ],
    ),

    "data-science-python": Course(
        name="data-science-python",
        level="advanced",
        description="NumPy, Pandas, SciPy, and Matplotlib for data science and visualisation.",
        steps=[
            CourseStep(step=1,  title="NumPy Intro",                 description="Arrays, shapes, and operations.", intent="concept"),
            CourseStep(step=2,  title="NumPy Exercise",              description="Perform array operations.", intent="exercise"),
            CourseStep(step=3,  title="Pandas DataFrames",           description="Create and analyse data with Pandas.", intent="concept"),
            CourseStep(step=4,  title="Pandas Exercise",             description="Filter, sort, and group data.", intent="exercise"),
            CourseStep(step=5,  title="SciPy Basics",               description="Scientific computing with SciPy.", intent="concept"),
            CourseStep(step=6,  title="Matplotlib Pyplot",           description="Basic plotting with pyplot.", intent="concept"),
            CourseStep(step=7,  title="Matplotlib Plotting",         description="Line, markers, and labels.", intent="concept"),
            CourseStep(step=8,  title="Matplotlib Scatter",          description="Scatter plots.", intent="concept"),
            CourseStep(step=9,  title="Matplotlib Bar Charts",       description="Bar and horizontal bar charts.", intent="concept"),
            CourseStep(step=10, title="Matplotlib Histograms",       description="Distribution visualisation.", intent="concept"),
            CourseStep(step=11, title="Matplotlib Pie Charts",       description="Pie and donut charts.", intent="concept"),
            CourseStep(step=12, title="Matplotlib Subplots",         description="Multiple plots in one figure.", intent="concept"),
            CourseStep(step=13, title="Data Science Quiz",           description="Test your data science knowledge.", intent="quiz"),
            CourseStep(step=14, title="Capstone Project",            description="Analyse a dataset and visualise 3 insights.", intent="codegen"),
        ],
    ),

    "python-databases": Course(
        name="python-databases",
        level="advanced",
        description="Python with MySQL and MongoDB — full database integration.",
        steps=[
            CourseStep(step=1,  title="MySQL Get Started",           description="Connect Python to MySQL with mysql-connector.", intent="concept"),
            CourseStep(step=2,  title="MySQL Create Database",       description="Create a database from Python.", intent="codegen"),
            CourseStep(step=3,  title="MySQL Create Table",          description="Define tables with Python.", intent="codegen"),
            CourseStep(step=4,  title="MySQL Insert",                description="Insert rows with parameterised queries.", intent="concept"),
            CourseStep(step=5,  title="MySQL Select",                description="Fetch and display records.", intent="concept"),
            CourseStep(step=6,  title="MySQL Where & Order By",      description="Filter and sort results.", intent="concept"),
            CourseStep(step=7,  title="MySQL Update & Delete",       description="Modify and remove records.", intent="concept"),
            CourseStep(step=8,  title="MySQL Join",                  description="Join tables in queries.", intent="concept"),
            CourseStep(step=9,  title="MySQL Exercise",              description="Build a CRUD app with MySQL.", intent="exercise"),
            CourseStep(step=10, title="MongoDB Get Started",         description="Connect Python to MongoDB with pymongo.", intent="concept"),
            CourseStep(step=11, title="MongoDB CRUD",                description="Insert, find, query, update, delete.", intent="concept"),
            CourseStep(step=12, title="MongoDB Exercise",            description="Build a document-based data store.", intent="exercise"),
            CourseStep(step=13, title="Databases Quiz",              description="Test your database knowledge.", intent="quiz"),
            CourseStep(step=14, title="Capstone Project",            description="Build a Python REST API backed by MySQL.", intent="codegen"),
        ],
    ),

    "numpy-mastery": Course(
        name="numpy-mastery",
        level="advanced",
        description="Complete NumPy — arrays, indexing, random, ufuncs, and statistical distributions.",
        steps=[
            CourseStep(step=1,  title="NumPy Intro & Getting Started",   description="What NumPy is, why it's faster than lists, and how to install it.", intent="concept"),
            CourseStep(step=2,  title="Creating Arrays",                  description="np.array(), np.zeros(), np.ones(), np.arange(), np.linspace().", intent="concept"),
            CourseStep(step=3,  title="Array Indexing & Slicing",         description="1D, 2D, 3D indexing, negative indexing, and slice syntax.", intent="concept"),
            CourseStep(step=4,  title="Indexing Exercise",                description="Practice array indexing and slicing on 2D and 3D arrays.", intent="exercise"),
            CourseStep(step=5,  title="Array Shape & Reshape",            description="ndim, shape, size, reshape(), flatten(), ravel().", intent="concept"),
            CourseStep(step=6,  title="NumPy Data Types",                 description="dtypes, astype(), copy vs view.", intent="concept"),
            CourseStep(step=7,  title="Array Iterating",                  description="Iterating with nditer(), ndenumerate(), and broadcasting.", intent="concept"),
            CourseStep(step=8,  title="Join, Split, Search, Sort, Filter",description="concatenate(), stack(), split(), where(), sort(), filter.", intent="concept"),
            CourseStep(step=9,  title="NumPy Operations Exercise",        description="Build a data pipeline using array operations.", intent="exercise"),
            CourseStep(step=10, title="NumPy Random — Distributions",     description="Normal, Binomial, Poisson, Uniform, Exponential, Chi-Square.", intent="concept"),
            CourseStep(step=11, title="Random Exercise",                  description="Simulate real-world data using NumPy random distributions.", intent="exercise"),
            CourseStep(step=12, title="ufunc Intro & Arithmetic",         description="Universal functions, frompyfunc(), add, subtract, multiply.", intent="concept"),
            CourseStep(step=13, title="ufunc Math Operations",            description="Logs, rounding, summation, products, differences, LCM, GCD.", intent="concept"),
            CourseStep(step=14, title="ufunc Trig & Set Operations",      description="sin, cos, tan, arcsin, hyperbolic, union, intersect, setdiff.", intent="concept"),
            CourseStep(step=15, title="NumPy Quiz",                       description="Test your full NumPy knowledge.", intent="quiz"),
            CourseStep(step=16, title="Capstone Project",                 description="Build a statistical analysis tool using NumPy arrays and ufuncs.", intent="codegen"),
        ],
    ),
    "pandas-mastery": Course(
        name="pandas-mastery",
        level="advanced",
        description="Complete Pandas — Series, DataFrames, CSV/JSON, data cleaning, analysis, and plotting.",
        steps=[
            CourseStep(step=1,  title="Pandas Intro & Getting Started",   description="What Pandas is, Series vs DataFrame, installation.", intent="concept"),
            CourseStep(step=2,  title="Pandas Series",                    description="Creating Series from lists, dicts, scalars; index, values, dtype.", intent="concept"),
            CourseStep(step=3,  title="Pandas DataFrames",                description="Creating DataFrames, loc, iloc, accessing columns and rows.", intent="concept"),
            CourseStep(step=4,  title="DataFrame Exercise",               description="Build and query a multi-column DataFrame.", intent="exercise"),
            CourseStep(step=5,  title="Read CSV & JSON",                  description="pd.read_csv(), pd.read_json(), head(), tail(), info().", intent="concept"),
            CourseStep(step=6,  title="Analyzing Data",                   description="describe(), mean(), median(), mode(), std(), count(), value_counts().", intent="concept"),
            CourseStep(step=7,  title="Data Analysis Exercise",           description="Analyze a sample sales dataset and extract insights.", intent="exercise"),
            CourseStep(step=8,  title="Cleaning Empty Cells",             description="dropna(), fillna(), interpolate(), isnull(), notnull().", intent="concept"),
            CourseStep(step=9,  title="Cleaning Wrong Format & Data",     description="to_datetime(), astype(), str methods, apply(), replace().", intent="concept"),
            CourseStep(step=10, title="Removing Duplicates",              description="duplicated(), drop_duplicates(), reset_index().", intent="concept"),
            CourseStep(step=11, title="Data Cleaning Exercise",           description="Clean a messy real-world dataset from scratch.", intent="exercise"),
            CourseStep(step=12, title="Pandas Correlations",              description="corr(), corrwith(), heatmap interpretation, feature relationships.", intent="concept"),
            CourseStep(step=13, title="Pandas Plotting",                  description="df.plot(), line, bar, hist, scatter, pie — built-in matplotlib integration.", intent="concept"),
            CourseStep(step=14, title="Pandas Quiz",                      description="Test your full Pandas knowledge.", intent="quiz"),
            CourseStep(step=15, title="Capstone Project",                 description="Perform end-to-end EDA on a real dataset: load, clean, analyse, visualise.", intent="codegen"),
        ],
    ),
    "web-apis": Course(
        name="web-apis",
        level="advanced",
        description="Build and consume REST APIs with FastAPI and the requests library.",
        steps=[
            CourseStep(step=1,  title="HTTP & REST Basics",          description="How the web works.", intent="concept"),
            CourseStep(step=2,  title="Requests Module",             description="Fetch data from a public API.", intent="codegen"),
            CourseStep(step=3,  title="FastAPI Intro",               description="Build your first FastAPI endpoint.", intent="concept"),
            CourseStep(step=4,  title="FastAPI Exercise",            description="Add a new route to a FastAPI app.", intent="exercise"),
            CourseStep(step=5,  title="Flask Basics",                description="Build a web app with Flask.", intent="concept"),
            CourseStep(step=6,  title="Flask Exercise",              description="Add routes to a Flask app.", intent="exercise"),
            CourseStep(step=7,  title="Django Overview",             description="Introduction to Django for web development.", intent="concept"),
            CourseStep(step=8,  title="APIs Quiz",                   description="Test your API knowledge.", intent="quiz"),
            CourseStep(step=9,  title="Capstone Project",            description="Build a documented REST API with FastAPI.", intent="codegen"),
        ],
    ),

    "prompt-engineering": Course(
        name="prompt-engineering",
        level="advanced",
        description="Master prompt engineering — write effective prompts for AI models.",
        steps=[
            CourseStep(step=1,  title="What is Prompt Engineering",  description="Introduction to prompting AI systems.", intent="concept"),
            CourseStep(step=2,  title="Zero-shot Prompting",         description="Getting results without examples.", intent="concept"),
            CourseStep(step=3,  title="Few-shot Prompting",          description="Using examples to guide AI output.", intent="concept"),
            CourseStep(step=4,  title="Chain-of-thought Prompting",  description="Step-by-step reasoning prompts.", intent="concept"),
            CourseStep(step=5,  title="Prompt Exercise",             description="Write prompts for real Python tasks.", intent="exercise"),
            CourseStep(step=6,  title="Prompt Templates",            description="Build reusable prompt templates in Python.", intent="codegen"),
            CourseStep(step=7,  title="AI Integration",              description="Call AI APIs from Python code.", intent="codegen"),
            CourseStep(step=8,  title="Prompt Engineering Quiz",     description="Test your prompting knowledge.", intent="quiz"),
            CourseStep(step=9,  title="Capstone Project",            description="Build a Python-powered AI assistant.", intent="codegen"),
        ],
    ),
}

# ---------------------------------------------------------------------------
# Learning path per level
# ---------------------------------------------------------------------------

PROJECT_PATHS: dict[str, list[str]] = {
    "beginner": [
        "python-fundamentals",
        "python-strings",
        "python-collections",
        "python-control-flow",
    ],
    "intermediate": [
        "python-fundamentals",
        "python-strings",
        "python-collections",
        "python-control-flow",
        "python-functions-advanced",
        "python-oop",
        "python-modules-stdlib",
    ],
    "advanced": [
        "python-fundamentals",
        "python-strings",
        "python-collections",
        "python-control-flow",
        "python-functions-advanced",
        "python-oop",
        "python-modules-stdlib",
        "python-dsa",
        "numpy-mastery",
        "pandas-mastery",
        "data-science-python",
        "python-databases",
        "web-apis",
        "prompt-engineering",
    ],
}


def get_course(name: str) -> Course | None:
    return COURSES.get(name)


def get_courses_for_level(level: str) -> list[Course]:
    names = PROJECT_PATHS.get(level, [])
    return [COURSES[n] for n in names if n in COURSES]


def get_all_courses() -> list[Course]:
    return list(COURSES.values())
