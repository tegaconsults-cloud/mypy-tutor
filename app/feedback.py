"""
Feedback store for MyPy Tutor.
Ratings and surveys are persisted to SQLite on every write so data survives
Render ephemeral restarts. All feedback is also forwarded by email to the
admin inbox via Gmail SMTP (fire-and-forget, non-blocking).
"""

import os
import time
import logging
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from app.models import MessageFeedback, SurveyFeedback, FeedbackSummary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Email config — read lazily at send time so Render env vars are always current
# ---------------------------------------------------------------------------

ADMIN_EMAIL = "tega.com.ng@gmail.com"   # all feedback forwarded here


def _send_feedback_email(subject: str, html_body: str, text_body: str) -> None:
    """Send feedback notification to admin in a daemon thread. Silent on failure."""
    import threading
    threading.Thread(
        target=_do_send_feedback,
        args=(subject, html_body, text_body),
        daemon=False,
    ).start()


def _do_send_feedback(subject: str, html_body: str, text_body: str) -> None:
    """Actual SMTP send — runs in daemon thread, reads env vars at call time."""
    email_user = os.getenv("EMAIL_USER", "")
    email_pass = os.getenv("EMAIL_PASS", "")
    email_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    email_port = int(os.getenv("EMAIL_PORT", "587"))
    email_from = os.getenv("EMAIL_FROM", f"MyPy Tutor <{email_user}>")

    if not email_user or not email_pass:
        logger.info("Email not configured — feedback stored locally only")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = email_from
        msg["To"]      = ADMIN_EMAIL
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(email_host, email_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(email_user, email_pass)
            server.sendmail(email_user, [ADMIN_EMAIL], msg.as_string())
        logger.info("Feedback email sent to %s", ADMIN_EMAIL)
    except Exception as exc:
        logger.warning("Feedback email failed: %s", exc)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

@dataclass
class _Rating:
    learner_id: str
    rating:     str
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
_interaction_count: dict[str, int] = {}
SURVEY_EVERY = 5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_message_feedback(fb: MessageFeedback) -> None:
    """Store thumbs rating in memory + SQLite, and email admin."""
    r = _Rating(
        learner_id=fb.learner_id,
        rating=fb.rating,
        intent=fb.intent,
        topic=fb.topic,
        comment=fb.comment,
    )
    _ratings.append(r)

    # Persist to PostgreSQL so feedback survives restarts
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "INSERT INTO feedback_ratings (learner_id, rating, intent, topic, comment) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (fb.learner_id, fb.rating, fb.intent or '', fb.topic or '', fb.comment or '')
                )
    except Exception as exc:
        logger.debug("Feedback DB save failed (non-fatal): %s", exc)

    emoji   = "👍" if fb.rating == "up" else "👎"
    ts      = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    subject = f"[MyPy Tutor] {emoji} Quick feedback from learner {fb.learner_id}"

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;background:#1a202c;color:#e2e8f0;padding:24px;border-radius:12px;border:1px solid #2d3748;">
  <h2 style="color:#63b3ed;margin-bottom:12px;">🐍 MyPy Tutor — Quick Feedback</h2>
  <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
    <tr><td style="padding:6px 0;color:#718096;width:140px;">Rating</td><td><strong style="font-size:1.2rem;">{emoji} {fb.rating.upper()}</strong></td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Learner ID</td><td>{fb.learner_id}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Topic</td><td>{fb.topic or '—'}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Intent</td><td>{fb.intent or '—'}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Comment</td><td>{fb.comment or '—'}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Time</td><td>{ts}</td></tr>
  </table>
</div>"""
    text = f"Rating: {fb.rating}\nLearner: {fb.learner_id}\nTopic: {fb.topic}\nComment: {fb.comment}\nTime: {ts}"
    _send_feedback_email(subject, html, text)


def record_survey(fb: SurveyFeedback) -> None:
    """Store full survey response in memory + SQLite, and email admin."""
    s = _Survey(
        learner_id=fb.learner_id,
        overall=fb.overall,
        clarity=fb.clarity,
        helpfulness=fb.helpfulness,
        suggestion=fb.suggestion,
        would_recommend=fb.would_recommend,
    )
    _surveys.append(s)

    # Persist to PostgreSQL so surveys survive restarts
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "INSERT INTO feedback_surveys "
                    "(learner_id, overall, clarity, helpfulness, suggestion, would_recommend) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (fb.learner_id, fb.overall, fb.clarity, fb.helpfulness,
                     fb.suggestion or '', int(fb.would_recommend))
                )
    except Exception as exc:
        logger.debug("Survey DB save failed (non-fatal): %s", exc)

    stars   = "⭐" * fb.overall
    ts      = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    subject = f"[MyPy Tutor] 📋 Survey ({fb.overall}/5 stars) from learner {fb.learner_id}"

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;background:#1a202c;color:#e2e8f0;padding:24px;border-radius:12px;border:1px solid #2d3748;">
  <h2 style="color:#63b3ed;margin-bottom:12px;">🐍 MyPy Tutor — Survey Response</h2>
  <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
    <tr><td style="padding:6px 0;color:#718096;width:160px;">Learner ID</td><td>{fb.learner_id}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Overall</td><td>{stars} ({fb.overall}/5)</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Clarity</td><td>{"⭐"*fb.clarity} ({fb.clarity}/5)</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Helpfulness</td><td>{"⭐"*fb.helpfulness} ({fb.helpfulness}/5)</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Would recommend</td><td>{"✅ Yes" if fb.would_recommend else "❌ No"}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;vertical-align:top;">Suggestion</td>
        <td style="background:#0f1117;padding:10px;border-radius:6px;">{fb.suggestion or '—'}</td></tr>
    <tr><td style="padding:6px 0;color:#718096;">Time</td><td>{ts}</td></tr>
  </table>
</div>"""
    text = (
        f"Overall: {fb.overall}/5\nClarity: {fb.clarity}/5\nHelpfulness: {fb.helpfulness}/5\n"
        f"Recommend: {fb.would_recommend}\nSuggestion: {fb.suggestion}\n"
        f"Learner: {fb.learner_id}\nTime: {ts}"
    )
    _send_feedback_email(subject, html, text)


def increment_interaction(learner_id: str) -> bool:
    _interaction_count[learner_id] = _interaction_count.get(learner_id, 0) + 1
    return _interaction_count[learner_id] % SURVEY_EVERY == 0


def get_summary() -> FeedbackSummary:
    """Build the feedback summary by querying PostgreSQL directly.

    The in-memory lists (_ratings, _surveys) reset on every Render restart,
    so they are only used as a fast path when they happen to be populated.
    The DB is always the authoritative source.
    """
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                # Rating counts
                _cur.execute("SELECT COUNT(*) FROM feedback_ratings")
                total = (_cur.fetchone() or [0])[0]

                _cur.execute("SELECT COUNT(*) FROM feedback_ratings WHERE rating='up'")
                ups = (_cur.fetchone() or [0])[0]

                # Survey aggregates
                _cur.execute("""
                    SELECT
                        COUNT(*),
                        COALESCE(AVG(overall), 0),
                        COALESCE(AVG(clarity), 0),
                        COALESCE(AVG(helpfulness), 0)
                    FROM feedback_surveys
                """)
                row = _cur.fetchone() or (0, 0, 0, 0)
                total_surveys   = int(row[0])
                avg_overall     = round(float(row[1]), 2)
                avg_clarity     = round(float(row[2]), 2)
                avg_helpfulness = round(float(row[3]), 2)

                # Recent non-empty suggestions (last 10)
                _cur.execute("""
                    SELECT suggestion FROM feedback_surveys
                    WHERE suggestion <> ''
                    ORDER BY id DESC LIMIT 10
                """)
                recent_suggestions = [r[0] for r in _cur.fetchall()]

        downs = total - ups
        pct   = round((ups / total * 100), 1) if total else 0.0

        return FeedbackSummary(
            total_ratings=total,
            thumbs_up=ups,
            thumbs_down=downs,
            satisfaction_pct=pct,
            avg_overall=avg_overall,
            avg_clarity=avg_clarity,
            avg_helpfulness=avg_helpfulness,
            total_surveys=total_surveys,
            recent_suggestions=recent_suggestions,
        )
    except Exception as exc:
        logger.warning("get_summary DB query failed, falling back to in-memory: %s", exc)
        # Fallback to in-memory data (e.g. during tests with no DB)
        total = len(_ratings)
        ups   = sum(1 for r in _ratings if r.rating == "up")
        downs = total - ups
        pct   = round((ups / total * 100), 1) if total else 0.0

        def avg(vals: list) -> float:
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        return FeedbackSummary(
            total_ratings=total,
            thumbs_up=ups,
            thumbs_down=downs,
            satisfaction_pct=pct,
            avg_overall=avg([s.overall      for s in _surveys]),
            avg_clarity=avg([s.clarity      for s in _surveys]),
            avg_helpfulness=avg([s.helpfulness  for s in _surveys]),
            total_surveys=len(_surveys),
            recent_suggestions=[
                s.suggestion for s in reversed(_surveys) if s.suggestion.strip()
            ][:10],
        )
