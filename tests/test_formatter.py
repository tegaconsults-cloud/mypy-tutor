"""
Unit tests for app/formatter.py — format_response and topic detection.
Validates: Requirements 7.4
"""

import pytest
from app.formatter import format_response, _detect_topic
from app.topics import SUPPORTED_TOPICS


# ---------------------------------------------------------------------------
# format_response — return structure
# ---------------------------------------------------------------------------

class TestFormatResponseStructure:
    def test_returns_dict(self):
        result = format_response("Some content about loops.", "concept")
        assert isinstance(result, dict)

    def test_has_intent_key(self):
        result = format_response("content", "debug")
        assert "intent" in result

    def test_has_content_key(self):
        result = format_response("content", "debug")
        assert "content" in result

    def test_has_topic_key(self):
        result = format_response("content", "debug")
        assert "topic" in result

    def test_intent_value_matches_input(self):
        for intent in ("concept", "debug", "codegen", "exercise", "ambiguous"):
            result = format_response("some text", intent)
            assert result["intent"] == intent

    def test_content_value_matches_input(self):
        body = "Here is an explanation of **functions** in Python."
        result = format_response(body, "concept")
        assert result["content"] == body

    def test_topic_is_none_when_no_match(self):
        result = format_response("This is completely unrelated text.", "concept")
        assert result["topic"] is None

    def test_only_three_keys(self):
        result = format_response("content", "concept")
        assert set(result.keys()) == {"intent", "content", "topic"}


# ---------------------------------------------------------------------------
# _detect_topic — direct topic name matching (case-insensitive)
# ---------------------------------------------------------------------------

class TestDetectTopicDirectMatch:
    @pytest.mark.parametrize("topic", SUPPORTED_TOPICS)
    def test_detects_each_supported_topic_exact(self, topic):
        """Every supported topic should be detected when it appears verbatim."""
        assert _detect_topic(topic) == topic

    @pytest.mark.parametrize("topic", SUPPORTED_TOPICS)
    def test_detects_each_supported_topic_uppercase(self, topic):
        """Detection is case-insensitive."""
        assert _detect_topic(topic.upper()) == topic

    @pytest.mark.parametrize("topic", SUPPORTED_TOPICS)
    def test_detects_topic_embedded_in_sentence(self, topic):
        """Topic keyword embedded in a longer sentence should still be detected."""
        content = f"Today we will learn about {topic} in Python."
        assert _detect_topic(content) == topic

    def test_returns_none_for_empty_string(self):
        assert _detect_topic("") is None

    def test_returns_none_for_unrelated_content(self):
        assert _detect_topic("The weather is nice today.") is None


# ---------------------------------------------------------------------------
# _detect_topic — alias matching
# ---------------------------------------------------------------------------

class TestDetectTopicAliases:
    def test_alias_variable_maps_to_variables(self):
        assert _detect_topic("A variable stores a value.") == "variables"

    def test_alias_loop_maps_to_loops(self):
        assert _detect_topic("Use a loop to iterate.") == "loops"

    def test_alias_function_maps_to_functions(self):
        assert _detect_topic("Define a function with def.") == "functions"

    def test_alias_exception_maps_to_exception_handling(self):
        assert _detect_topic("Catch an exception with try/except.") == "exception handling"

    def test_alias_algorithm_maps_to_algorithms(self):
        assert _detect_topic("This algorithm runs in O(n).") == "algorithms"

    def test_alias_flask_maps_to_flask_basics(self):
        assert _detect_topic("Build a route with Flask.") == "Flask basics"

    def test_alias_fastapi_maps_to_fastapi_basics(self):
        assert _detect_topic("FastAPI makes it easy to build web services.") == "FastAPI basics"

    def test_alias_inheritance_maps_to_oop(self):
        assert _detect_topic("Inheritance is a key OOP concept.") == "OOP"

    def test_alias_dictionary_maps_to_data_structures(self):
        assert _detect_topic("A dictionary maps keys to values.") == "data structures"

    def test_alias_recursion_maps_to_algorithms(self):
        assert _detect_topic("Recursion calls the function itself.") == "algorithms"


# ---------------------------------------------------------------------------
# format_response — topic detection integration
# ---------------------------------------------------------------------------

class TestFormatResponseTopicDetection:
    def test_detects_loops_topic(self):
        result = format_response("Let me explain loops in Python.", "concept")
        assert result["topic"] == "loops"

    def test_detects_functions_topic(self):
        result = format_response("Here is how functions work.", "concept")
        assert result["topic"] == "functions"

    def test_detects_oop_topic(self):
        result = format_response("OOP stands for Object-Oriented Programming.", "concept")
        assert result["topic"] == "OOP"

    def test_detects_flask_basics_topic(self):
        result = format_response("Flask basics include routing and templates.", "concept")
        assert result["topic"] == "Flask basics"

    def test_detects_fastapi_basics_topic(self):
        result = format_response("FastAPI basics cover path parameters.", "concept")
        assert result["topic"] == "FastAPI basics"

    def test_no_topic_for_unrelated_content(self):
        result = format_response("The sky is blue.", "ambiguous")
        assert result["topic"] is None
