from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import ChatRequest, Message

# Feature: ai-python-tutor, Property 7: Request/response model round-trip

message_strategy = st.builds(
    Message,
    role=st.sampled_from(["user", "assistant"]),
    content=st.text(),
)

chat_request_strategy = st.builds(
    ChatRequest,
    message=st.text(),
    history=st.lists(message_strategy),
)


@settings(max_examples=100)
@given(req=chat_request_strategy)
def test_chat_request_json_round_trip(req: ChatRequest):
    """
    Property 7: Request/response model round-trip
    Validates: Requirements 5.1
    For any valid ChatRequest, serializing to JSON and deserializing produces an equivalent object.
    """
    assert ChatRequest.model_validate(req.model_dump()) == req
