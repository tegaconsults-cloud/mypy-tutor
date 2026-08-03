"""
One-shot script: replaces send_announcement in admin.py with the
SQLite-backed version that reads all 64 users, not just in-memory ones.
"""
import re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "app", "admin.py")

with open(path, encoding="utf-8") as f:
    src = f.read()

OLD_PATTERN = (
    r"async def send_announcement\(target: str, subject: str, body_text: str\) -> int:.*?"
    r"return sent\n"
)

NEW_FUNC = '''\
async def send_announcement(target: str, subject: str, body_text: str) -> int:
    """
    Send announcement email to all matching users. Returns count sent.

    Source of truth: SQLite (persistent across Render restarts) — NOT the
    in-memory _confirmed / _store dicts, which are wiped on every Render
    restart and only contain users active since the last boot.
    Supabase is used as a final fallback if SQLite is also empty.
    """
    from app.db import get_db as _gdb

    seen_emails: set[str] = set()
    # { learner_id: (email, name, tier) }
    user_map: dict[str, tuple[str, str, str]] = {}

    # ── Source 1: learner_profiles — all users, carries email + tier ─────────────
    try:
        with _gdb() as conn:
            rows = conn.execute(
                "SELECT learner_id, email, display_name, tier FROM learner_profiles"
            ).fetchall()
        for r in rows:
            lid   = (r["learner_id"] or "").strip()
            email = (r["email"] or "").lower().strip()
            name  = (r["display_name"] or "").strip()
            tier  = (r["tier"] or "free").strip()
            if lid and email and "@" in email:
                user_map[lid] = (email, name, tier)
    except Exception as exc:
        logger.warning("send_announcement: learner_profiles query failed: %s", exc)

    # ── Source 2: email_accounts — confirmed users, carries proper full name ──────
    try:
        with _gdb() as conn:
            rows = conn.execute(
                "SELECT learner_id, email, name FROM email_accounts WHERE confirmed=1"
            ).fetchall()
        for r in rows:
            lid   = (r["learner_id"] or "").strip()
            email = (r["email"] or "").lower().strip()
            name  = (r["name"] or "").strip()
            if lid and email and "@" in email:
                existing = user_map.get(lid)
                tier     = existing[2] if existing else "free"
                # Prefer the proper full name from email_accounts
                best_name = name or (existing[1] if existing else "")
                user_map[lid] = (email, best_name, tier)
    except Exception as exc:
        logger.warning("send_announcement: email_accounts query failed: %s", exc)

    # ── Source 3: Supabase fallback (covers Render ephemeral-restart window) ──────
    if not user_map:
        logger.info("send_announcement: SQLite empty — falling back to Supabase")
        try:
            from app.supabase_client import get_supabase
            sb = get_supabase()
            if sb:
                res = sb.table("profiles").select("id,email,full_name").execute()
                for r in (res.data or []):
                    lid   = (r.get("id") or "").strip()
                    email = (r.get("email") or "").lower().strip()
                    name  = (r.get("full_name") or "").strip()
                    if lid and email and "@" in email:
                        user_map[lid] = (email, name, "free")
                # Overlay tiers from learner_progress table
                res2 = sb.table("learner_progress").select("learner_id,tier").execute()
                for r in (res2.data or []):
                    lid  = (r.get("learner_id") or "").strip()
                    tier = (r.get("tier") or "free").strip()
                    if lid in user_map:
                        e, n, _ = user_map[lid]
                        user_map[lid] = (e, n, tier)
        except Exception as exc:
            logger.warning("send_announcement: Supabase fallback failed: %s", exc)

    # ── Build deduplicated recipient list filtered by target tier ─────────────────
    recipients: list[tuple[str, str]] = []
    for lid, (email, name, tier) in user_map.items():
        if email in seen_emails:
            continue
        if _matches_target(target, tier):
            seen_emails.add(email)
            recipients.append((email, name or email.split("@")[0]))

    logger.info(
        "send_announcement: target=%s total_users=%d matching=%d",
        target, len(user_map), len(recipients),
    )

    if not recipients:
        _save_announcement_db(subject, target, 0)
        return 0

    try:
        from app.services.email_service import send_bulk_announcement
        sent = send_bulk_announcement(
            subject=subject,
            body_html=(
                "<p style='color:#475569;line-height:1.7;white-space:pre-wrap;'>"
                + body_text
                + "</p>"
            ),
            body_text=body_text,
            recipients=recipients,
            target_label=target,
        )
    except Exception as exc:
        logger.error("Announcement send failed: %s", exc)
        sent = 0

    record = {"subject": subject, "target": target, "sent_to": sent,
              "sent_at": datetime.now().isoformat()}
    _announcements.append(record)
    _save_announcement_db(subject, target, sent)
    return sent
'''

new_src = re.sub(OLD_PATTERN, NEW_FUNC, src, flags=re.DOTALL)
if new_src == src:
    print("ERROR: pattern not matched — no change written")
    sys.exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write(new_src)

print(f"OK  send_announcement replaced ({len(src)} → {len(new_src)} chars)")
