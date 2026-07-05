"""
Learner progress store — backed by SQLite for persistence across restarts.
Memory cache (_store) is used for fast reads; SQLite is the source of truth.
"""

import json
from app.models import LearnerProfile, TopicProgress
from app.db import load_profile, save_profile_db

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
    """
    Load profile with 3-tier fallback:
    1. In-memory cache (_store) — fastest, always checked first
    2. SQLite — persisted local DB
    3. Supabase — cloud source of truth, used when SQLite is empty after a restart
    """
    if learner_id in _store:
        return _store[learner_id]

    # Try loading from SQLite
    row = load_profile(learner_id)
    if row:
        tp_raw = json.loads(row.get("topic_progress", "{}"))
        topic_progress = {
            k: TopicProgress(**v) if isinstance(v, dict) else v
            for k, v in tp_raw.items()
        }
        profile = LearnerProfile(
            learner_id=learner_id,
            tier=row.get("tier", "free"),
            level=row.get("level", "beginner"),
            xp=row.get("xp", 0),
            badges=json.loads(row.get("badges", "[]")),
            topics_seen=json.loads(row.get("topics_seen", "[]")),
            topic_progress=topic_progress,
            current_course=row.get("current_course"),
            current_course_step=row.get("course_step", 0),
            completed_projects=json.loads(row.get("completed_projects", "[]")),
            daily_prompts_used=row.get("daily_prompts_used", 0),
            last_prompt_date=row.get("last_prompt_date", ""),
            email=row.get("email", ""),
            display_name=row.get("display_name", ""),
        )
        _store[learner_id] = profile
        return profile

    # SQLite miss — try Supabase directly (covers the window between restart and
    # background recovery completing, or first sign-in on a fresh deploy)
    try:
        from app.supabase_client import sb_load_progress, sb_enabled
        if sb_enabled():
            sb_row = sb_load_progress(learner_id)
            if sb_row:
                tp_raw = {}
                raw_tp = sb_row.get("topic_progress", "{}")
                if isinstance(raw_tp, str):
                    try:
                        tp_raw = json.loads(raw_tp)
                    except Exception:
                        tp_raw = {}
                elif isinstance(raw_tp, dict):
                    tp_raw = raw_tp

                topic_progress = {
                    k: TopicProgress(**v) if isinstance(v, dict) else v
                    for k, v in tp_raw.items()
                }
                badges_raw = sb_row.get("badges", "[]")
                topics_raw = sb_row.get("topics_seen", "[]")
                projects_raw = sb_row.get("completed_projects", "[]")

                profile = LearnerProfile(
                    learner_id=learner_id,
                    tier=sb_row.get("tier", "free"),
                    level=sb_row.get("level", "beginner"),
                    xp=sb_row.get("xp", 0),
                    badges=json.loads(badges_raw) if isinstance(badges_raw, str) else (badges_raw or []),
                    topics_seen=json.loads(topics_raw) if isinstance(topics_raw, str) else (topics_raw or []),
                    topic_progress=topic_progress,
                    current_course=sb_row.get("current_course"),
                    current_course_step=sb_row.get("current_course_step", 0),
                    completed_projects=json.loads(projects_raw) if isinstance(projects_raw, str) else (projects_raw or []),
                    daily_prompts_used=0,
                    last_prompt_date="",
                    email=sb_row.get("email", ""),
                    display_name=sb_row.get("display_name", ""),
                )
                _store[learner_id] = profile
                # Backfill SQLite so next request is fast
                _backfill_sqlite(learner_id, profile)
                return profile
    except Exception as sb_exc:
        import logging as _log
        _log.getLogger(__name__).debug("Supabase get_profile fallback failed for %s: %s", learner_id, sb_exc)

    # Truly new user — create blank profile
    profile = LearnerProfile(learner_id=learner_id)
    _store[learner_id] = profile
    return profile


def _backfill_sqlite(learner_id: str, profile: LearnerProfile) -> None:
    """Write a Supabase-recovered profile back to SQLite so reads are fast next time."""
    try:
        tp_dict = {k: v.model_dump() for k, v in profile.topic_progress.items()}
        save_profile_db(learner_id, {
            "tier":               profile.tier,
            "level":              profile.level,
            "xp":                 profile.xp,
            "badges":             profile.badges,
            "topics_seen":        profile.topics_seen,
            "topic_progress":     tp_dict,
            "current_course":     profile.current_course,
            "current_course_step":profile.current_course_step,
            "completed_projects": profile.completed_projects,
            "daily_prompts_used": profile.daily_prompts_used,
            "last_prompt_date":   profile.last_prompt_date,
            "email":              profile.email,
            "display_name":       profile.display_name,
        })
    except Exception:
        pass


def save_profile(profile: LearnerProfile) -> None:
    """Save to memory cache + SQLite (sync). Supabase sync is a background fire-and-forget."""
    _store[profile.learner_id] = profile
    tp_dict = {
        k: v.model_dump() for k, v in profile.topic_progress.items()
    }
    profile_data = {
        "tier":               profile.tier,
        "level":              profile.level,
        "xp":                 profile.xp,
        "badges":             profile.badges,
        "topics_seen":        profile.topics_seen,
        "topic_progress":     tp_dict,
        "current_course":     profile.current_course,
        "current_course_step":profile.current_course_step,
        "completed_projects": profile.completed_projects,
        "daily_prompts_used": profile.daily_prompts_used,
        "last_prompt_date":   profile.last_prompt_date,
        "email":              profile.email,
        "display_name":       profile.display_name,
    }
    save_profile_db(profile.learner_id, profile_data)
    # Supabase sync — non-daemon thread so it finishes before process exits on SIGTERM
    try:
        from app.supabase_client import sb_sync_progress
        import threading
        threading.Thread(
            target=sb_sync_progress,
            args=(profile.learner_id, profile_data),
            daemon=False,   # non-daemon: process waits for this on shutdown
            name=f"sb-sync-{profile.learner_id[:12]}",
        ).start()
    except Exception:
        pass


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
