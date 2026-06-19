"""
In-memory feedback store for MyPy Tutor.
Stores thumbs ratings and survey responses per learner.
"""

import time
from dataclasses import dataclass, field
from app.models import MessageFeedback, SurveyFeedback, FeedbackSummary

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

@dataclass
class _Rating:
    learner_id: str
    rating:     str          # "up" | "down"
    intent:     str
    topic:      str
    comment:    str
    ts:         float = field(default_factory=time.time)


@dataclass
class _Survey:
    learner_id:      str
    overall:         int
    clarity:         int
    helpfulness:     int
    suggestion:      str
    would_recommend: bool
    ts:              float = field(default_factory=time.time)


_ratings:  list[_Rating] = []
_surveys:  list[_Survey] = []

# Interaction counter per learner — triggers periodic survey prompt
_interaction_count: dict[str, int] = {}
SURVEY_EVERY = 5     # ask for full survey every N chat interactions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_message_feedback(fb: MessageFeedback) -> None:
    _ratings.append(_Rating(
        learner_id=fb.learner_id,
        rating=fb.rating,
        intent=fb.intent,
        topic=fb.topic,
        comment=fb.comment,
    ))


def record_survey(fb: SurveyFeedback) -> None:
    _surveys.append(_Survey(
        learner_id=fb.learner_id,
        overall=fb.overall,
        clarity=fb.clarity,
        helpfulness=fb.helpfulness,
        suggestion=fb.suggestion,
        would_recommend=fb.would_recommend,
    ))


def increment_interaction(learner_id: str) -> bool:
    """
    Increment the interaction counter for a learner.
    Returns True when it's time to show the survey prompt.
    """
    _interaction_count[learner_id] = _interaction_count.get(learner_id, 0) + 1
    return _interaction_count[learner_id] % SURVEY_EVERY == 0


def get_summary() -> FeedbackSummary:
    """Return aggregate feedback statistics."""
    total  = len(_ratings)
    ups    = sum(1 for r in _ratings if r.rating == "up")
    downs  = total - ups
    pct    = round((ups / total * 100), 1) if total else 0.0

    def avg(values):
        return round(sum(values) / len(values), 2) if values else 0.0

    overalls    = [s.overall     for s in _surveys]
    clarities   = [s.clarity     for s in _surveys]
    helpfulnesses = [s.helpfulness for s in _surveys]

    # Last 10 non-empty suggestions
    suggestions = [
        s.suggestion for s in reversed(_surveys)
        if s.suggestion.strip()
    ][:10]

    return FeedbackSummary(
        total_ratings=total,
        thumbs_up=ups,
        thumbs_down=downs,
        satisfaction_pct=pct,
        avg_overall=avg(overalls),
        avg_clarity=avg(clarities),
        avg_helpfulness=avg(helpfulnesses),
        total_surveys=len(_surveys),
        recent_suggestions=suggestions,
    )
