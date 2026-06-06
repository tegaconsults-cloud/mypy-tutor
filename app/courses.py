"""
Structured Python course definitions and project-based learning paths.
"""

from app.models import Course, CourseStep

COURSES: dict[str, Course] = {
    "python-fundamentals": Course(
        name="python-fundamentals",
        level="beginner",
        description="Master Python from zero — variables, loops, functions, and more.",
        steps=[
            CourseStep(step=1,  title="Variables & Data Types",   description="Learn how Python stores data.", intent="concept"),
            CourseStep(step=2,  title="Variables Exercise",        description="Practice declaring and using variables.", intent="exercise"),
            CourseStep(step=3,  title="Variables Quiz",            description="Test your variables knowledge.", intent="quiz"),
            CourseStep(step=4,  title="Loops",                     description="For-loops and while-loops explained.", intent="concept"),
            CourseStep(step=5,  title="Loops Exercise",            description="Write loop programs.", intent="exercise"),
            CourseStep(step=6,  title="Loops Quiz",                description="Test your loops knowledge.", intent="quiz"),
            CourseStep(step=7,  title="Functions",                 description="Define and call functions.", intent="concept"),
            CourseStep(step=8,  title="Functions Exercise",        description="Write your own functions.", intent="exercise"),
            CourseStep(step=9,  title="Functions Quiz",            description="Test your functions knowledge.", intent="quiz"),
            CourseStep(step=10, title="Exception Handling",        description="Handle errors gracefully.", intent="concept"),
            CourseStep(step=11, title="Exception Exercise",        description="Write try/except code.", intent="exercise"),
            CourseStep(step=12, title="Capstone Project",          description="Build a number-guessing game.", intent="codegen"),
        ],
    ),
    "oop-mastery": Course(
        name="oop-mastery",
        level="intermediate",
        description="Object-oriented Python — classes, inheritance, and design patterns.",
        steps=[
            CourseStep(step=1,  title="Classes & Objects",         description="What are classes and how to define them.", intent="concept"),
            CourseStep(step=2,  title="OOP Exercise",              description="Build a simple class.", intent="exercise"),
            CourseStep(step=3,  title="OOP Quiz",                  description="Test OOP fundamentals.", intent="quiz"),
            CourseStep(step=4,  title="Inheritance",               description="Subclasses and method overriding.", intent="concept"),
            CourseStep(step=5,  title="Inheritance Exercise",      description="Extend a class.", intent="exercise"),
            CourseStep(step=6,  title="Inheritance Quiz",          description="Test inheritance knowledge.", intent="quiz"),
            CourseStep(step=7,  title="Magic Methods",             description="__str__, __repr__, __len__ and more.", intent="concept"),
            CourseStep(step=8,  title="Magic Methods Exercise",    description="Implement dunder methods.", intent="exercise"),
            CourseStep(step=9,  title="Capstone Project",          description="Build a bank account class hierarchy.", intent="codegen"),
        ],
    ),
    "data-structures": Course(
        name="data-structures",
        level="intermediate",
        description="Lists, dicts, sets, stacks, queues, and algorithms.",
        steps=[
            CourseStep(step=1,  title="Lists & Tuples",            description="Sequence types in depth.", intent="concept"),
            CourseStep(step=2,  title="List Exercise",             description="Manipulate lists.", intent="exercise"),
            CourseStep(step=3,  title="Dictionaries & Sets",       description="Key-value storage and sets.", intent="concept"),
            CourseStep(step=4,  title="Dict Exercise",             description="Build a word frequency counter.", intent="exercise"),
            CourseStep(step=5,  title="Stacks & Queues",           description="Implement classic structures.", intent="concept"),
            CourseStep(step=6,  title="Algorithms",                description="Sorting and searching.", intent="concept"),
            CourseStep(step=7,  title="Algorithms Quiz",           description="Test algorithm knowledge.", intent="quiz"),
            CourseStep(step=8,  title="Capstone Project",          description="Build a task scheduler using a priority queue.", intent="codegen"),
        ],
    ),
    "web-apis": Course(
        name="web-apis",
        level="advanced",
        description="Build and consume REST APIs with FastAPI and the requests library.",
        steps=[
            CourseStep(step=1,  title="HTTP & REST Basics",        description="How the web works.", intent="concept"),
            CourseStep(step=2,  title="Using requests",            description="Fetch data from a public API.", intent="codegen"),
            CourseStep(step=3,  title="FastAPI Intro",             description="Build your first FastAPI endpoint.", intent="concept"),
            CourseStep(step=4,  title="FastAPI Exercise",          description="Add a new route to a FastAPI app.", intent="exercise"),
            CourseStep(step=5,  title="APIs Quiz",                 description="Test your API knowledge.", intent="quiz"),
            CourseStep(step=6,  title="Capstone Project",          description="Build a fully documented REST API with FastAPI.", intent="codegen"),
        ],
    ),
}

PROJECT_PATHS: dict[str, list[str]] = {
    "beginner":     ["python-fundamentals"],
    "intermediate": ["python-fundamentals", "oop-mastery", "data-structures"],
    "advanced":     ["python-fundamentals", "oop-mastery", "data-structures", "web-apis"],
}


def get_course(name: str) -> Course | None:
    return COURSES.get(name)


def get_courses_for_level(level: str) -> list[Course]:
    names = PROJECT_PATHS.get(level, [])
    return [COURSES[n] for n in names if n in COURSES]


def get_all_courses() -> list[Course]:
    return list(COURSES.values())
