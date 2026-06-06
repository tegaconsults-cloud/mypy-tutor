"""
In-memory learner progress store.
On Render free tier there is no persistent disk, so progress lives in memory
per-process (survives restarts only if the process stays up).
Swap _store for Redis/SQLite in production for true persistence.
"""

from app.models import LearnerProfile, TopicProgress

_store: dict[str, LearnerProfile] = {}

# XP rewards
XP_LESSON     = 10
XP_EXERCISE   = 20
XP_QUIZ_PASS  = 30
XP_PROJECT    = 100

# Level thresholds
LEVEL_UP = {"beginner": 200, "intermediate": 500}

BADGES = {
    "first_lesson":    "🎓 First Lesson",
    "debug_master":    "🐛 Debug Master",
    "code_creator":    "⚙️ Code Creator",
    "quiz_ace":        "🏆 Quiz Ace",
    "gap_closed":      "🔍 Gap Closer",
    "course_complete": "📚 Course Complete",
    "project_done":    "🚀 Project Builder",
    "level_up":        "⬆️ Level Up",
}


def get_profile(learner_id: str) -> LearnerProfile:
    if learner_id not in _store:
        _store[learner_id] = LearnerProfile(learner_id=learner_id)
    return _store[learner_id]


def save_profile(profile: LearnerProfile) -> None:
    _store[profile.learner_id] = profile


def _award_badge(profile: LearnerProfile, key: str) -> str | None:
    label = BADGES.get(key)
    if label and label not in profile.badges:
        profile.badges.append(label)
        return label
    return None


def _check_level_up(profile: LearnerProfile) -> bool:
    threshold = LEVEL_UP.get(profile.level)
    if threshold and profile.xp >= threshold:
        if profile.level == "beginner":
            profile.level = "intermediate"
        elif profile.level == "intermediate":
            profile.level = "advanced"
        _award_badge(profile, "level_up")
        return True
    return False


def record_lesson(learner_id: str, topic: str, intent: str) -> tuple[int, str | None]:
    """Record a completed lesson/concept/codegen interaction. Returns (xp_gained, badge)."""
    profile = get_profile(learner_id)

    # Track topic
    if topic and topic not in profile.topics_seen:
        profile.topics_seen.append(topic)

    if topic:
        tp = profile.topic_progress.setdefault(topic, TopicProgress(topic=topic))
        tp.lessons_completed += 1

    xp = XP_LESSON
    profile.xp += xp

    badge = None
    if len(profile.topics_seen) == 1:
        badge = _award_badge(profile, "first_lesson")
    if intent == "debug" and sum(
        tp.lessons_completed for tp in profile.topic_progress.values()
    ) >= 3:
        badge = badge or _award_badge(profile, "debug_master")
    if intent == "codegen" and sum(
        tp.lessons_completed for tp in profile.topic_progress.values()
    ) >= 5:
        badge = badge or _award_badge(profile, "code_creator")

    _check_level_up(profile)
    save_profile(profile)
    return xp, badge


def record_quiz(learner_id: str, topic: str, score: int) -> tuple[int, str | None]:
    """Record a quiz result (score 0–100). Returns (xp_gained, badge)."""
    profile = get_profile(learner_id)

    tp = profile.topic_progress.setdefault(topic, TopicProgress(topic=topic))
    tp.quiz_scores.append(score)

    # Mark as weak if last 3 attempts average < 60
    recent = tp.quiz_scores[-3:]
    avg = sum(recent) / len(recent)
    previously_weak = tp.weak
    tp.weak = avg < 60

    xp = XP_QUIZ_PASS if score >= 60 else 5
    profile.xp += xp

    badge = None
    if score == 100:
        badge = _award_badge(profile, "quiz_ace")
    if previously_weak and not tp.weak:
        badge = badge or _award_badge(profile, "gap_closed")

    _check_level_up(profile)
    save_profile(profile)
    return xp, badge


def record_exercise(learner_id: str, topic: str, passed: bool) -> tuple[int, str | None]:
    """Record an exercise attempt. Returns (xp_gained, badge)."""
    profile = get_profile(learner_id)
    tp = profile.topic_progress.setdefault(topic, TopicProgress(topic=topic))
    tp.exercises_attempted += 1
    if passed:
        tp.exercises_passed += 1

    xp = XP_EXERCISE if passed else 5
    profile.xp += xp

    _check_level_up(profile)
    save_profile(profile)
    return xp, None


def get_knowledge_gaps(learner_id: str) -> list[str]:
    """Return list of topics flagged as weak."""
    profile = get_profile(learner_id)
    return [t for t, tp in profile.topic_progress.items() if tp.weak]


def advance_course(learner_id: str) -> None:
    """Increment the learner's current course step."""
    profile = get_profile(learner_id)
    profile.current_course_step += 1
    save_profile(profile)


def complete_project(learner_id: str, project_name: str) -> tuple[int, str | None]:
    profile = get_profile(learner_id)
    if project_name not in profile.completed_projects:
        profile.completed_projects.append(project_name)
        profile.xp += XP_PROJECT
        badge = _award_badge(profile, "project_done")
        _check_level_up(profile)
        save_profile(profile)
        return XP_PROJECT, badge
    return 0, None
