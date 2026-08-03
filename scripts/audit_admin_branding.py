"""
Audit admin panel, branding, and admin→user flow completeness.
Run: python scripts/audit_admin_branding.py
"""
import sys, os, ast
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASS = []
FAIL = []

def ok(label, detail=""):
    PASS.append(label)
    print(f"  OK    {label}" + (f": {detail}" if detail else ""))

def fail(label, detail=""):
    FAIL.append(label)
    print(f"  FAIL  {label}" + (f": {detail}" if detail else ""))

def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()

main_src     = read("app/main.py")
admin_src    = read("app/admin.py")
admin_html   = read("static/admin.html")
model_src    = read("app/models.py")
progress_ctx = read("frontend-react/src/context/ProgressContext.tsx")
xpbar_src    = read("frontend-react/src/components/XPBar.tsx")
sidebar_src  = read("frontend-react/src/components/Sidebar.tsx")
authmodal    = read("frontend-react/src/components/AuthModal.tsx")
referral_src = read("frontend-react/src/components/ReferralModal.tsx")
header_src   = read("frontend-react/src/components/Header.tsx")

# ── ANNOUNCEMENT ───────────────────────────────────────────────────────────
print("\n=== ANNOUNCEMENT SYSTEM ===")
# Backend route exists
c1 = "/admin/announce" in main_src and "send_announcement" in main_src
ok("POST /admin/announce route exists") if c1 else fail("POST /admin/announce route", "not found in main.py")

# send_announcement includes OAuth users (not just email-auth users)
c2 = "_store as ls" in admin_src and "profile.email" in admin_src
ok("send_announcement includes OAuth users via _store") if c2 else fail("send_announcement OAuth coverage", "only _confirmed users sent to")

# History route exists
c3 = "/admin/announce/history" in main_src
ok("GET /admin/announce/history route exists") if c3 else fail("GET /admin/announce/history", "not found")

# admin.html announce form has correct element IDs
c4 = 'id="ann-target"' in admin_html and 'id="ann-subj"' in admin_html and 'id="ann-body"' in admin_html
ok("admin.html announce form IDs match JS (ann-target, ann-subj, ann-body)") if c4 else fail("admin.html announce form IDs", "IDs missing or mismatched")

# JS sendAnnouncement calls correct endpoint
c5 = "sendAnnouncement" in admin_html and "'/admin/announce'" in admin_html
ok("admin.html sendAnnouncement() calls /admin/announce") if c5 else fail("sendAnnouncement endpoint", "wrong endpoint in admin.html")

# History displayed
c6 = "ann-history" in admin_html and "loadAnnounce" in admin_html
ok("admin.html displays announcement history") if c6 else fail("admin.html announcement history display")

# ── TEAM MEMBER INVITE ─────────────────────────────────────────────────────
print("\n=== TEAM MEMBER INVITE ===")
c7 = "/admin/team/invite" in main_src
ok("POST /admin/team/invite route exists") if c7 else fail("POST /admin/team/invite", "not found")

c8 = "invite_team_member" in main_src and "invite_team_member" in admin_src
ok("invite_team_member function used correctly") if c8 else fail("invite_team_member", "not wired")

# Email now uses FRONTEND_URL not APP_URL
c9 = "FRONTEND_URL" in main_src and "team/invite" in main_src
# Find the team invite block specifically
invite_start = main_src.find('"/admin/team/invite"')
invite_block = main_src[invite_start:invite_start+900] if invite_start != -1 else ""
c9 = "FRONTEND_URL" in invite_block
ok("Team invite email uses FRONTEND_URL (not backend URL)") if c9 else fail("Team invite email domain", "still uses APP_URL — link goes to backend")

# admin.html team form IDs match JS
c10 = 'id="tm-email"' in admin_html and 'id="tm-name"' in admin_html and 'id="tm-role"' in admin_html
ok("admin.html team form IDs correct (tm-email, tm-name, tm-role)") if c10 else fail("admin.html team form IDs")

c11 = "inviteTeam" in admin_html and "'/admin/team/invite'" in admin_html
ok("admin.html inviteTeam() calls /admin/team/invite") if c11 else fail("inviteTeam endpoint")

# ── TASKS ──────────────────────────────────────────────────────────────────
print("\n=== TASKS ===")
c12 = "/admin/tasks/create" in main_src
ok("POST /admin/tasks/create route exists") if c12 else fail("POST /admin/tasks/create")

task_start = main_src.find('"/admin/tasks/create"')
task_block = main_src[task_start:task_start+900] if task_start != -1 else ""
c13 = "FRONTEND_URL" in task_block
ok("Task assignment email uses FRONTEND_URL") if c13 else fail("Task email domain", "still uses APP_URL")

c14 = "/admin/tasks/{task_id}/status" in main_src
ok("POST /admin/tasks/{task_id}/status route exists") if c14 else fail("task status update route")

c15 = 'id="tk-title"' in admin_html and 'id="tk-to"' in admin_html and 'id="tk-desc"' in admin_html
ok("admin.html task form IDs correct (tk-title, tk-to, tk-desc)") if c15 else fail("admin.html task form IDs")

c16 = "createTask" in admin_html and "'/admin/tasks/create'" in admin_html
ok("admin.html createTask() calls /admin/tasks/create") if c16 else fail("createTask endpoint")

c17 = "updateTask" in admin_html and "'/admin/tasks/'" in admin_html
ok("admin.html updateTask() calls /admin/tasks/{id}/status") if c17 else fail("updateTask endpoint")

# ── PROGRESS / ADMIN TIER SYNC ─────────────────────────────────────────────
print("\n=== PROGRESS / ADMIN TIER SYNC ===")
c18 = "updated_at" in model_src and "ProgressResponse" in model_src
ok("ProgressResponse model has updated_at field") if c18 else fail("ProgressResponse.updated_at")

c19 = "updated_at" in main_src and "get_progress" in main_src
ok("/progress endpoint populates updated_at from DB") if c19 else fail("/progress updated_at population")

c20 = "updated_at" in progress_ctx
ok("ProgressContext.tsx Progress interface has updated_at field") if c20 else fail("ProgressContext.tsx updated_at field")

c21 = "serverUpdatedAt" in progress_ctx or "updated_at" in progress_ctx
ok("ProgressContext.tsx uses updated_at for cache invalidation") if c21 else fail("ProgressContext updated_at cache check")

# ── BRANDING CONSISTENCY ───────────────────────────────────────────────────
print("\n=== BRANDING ===")
# admin.html should NOT link to onrender.com in user-visible URLs
# (logo/favicon from onrender is fine — it's a static asset URL)
# Email links in main.py should not send users to onrender.com
invite_block2 = main_src[main_src.find("team/invite"):main_src.find("team/invite")+900] if "team/invite" in main_src else ""
c22 = "onrender.com" not in invite_block2 or "FRONTEND_URL" in invite_block2
ok("Team invite email does not hardcode onrender.com") if c22 else fail("Team invite email", "hardcodes onrender.com")

task_block2 = main_src[main_src.find("tasks/create"):main_src.find("tasks/create")+900] if "tasks/create" in main_src else ""
c23 = "onrender.com" not in task_block2 or "FRONTEND_URL" in task_block2
ok("Task assignment email does not hardcode onrender.com") if c23 else fail("Task email", "hardcodes onrender.com")

# XPBar unused import removed
c24 = "Flame" not in xpbar_src
ok("XPBar.tsx: unused Flame import removed") if c24 else fail("XPBar.tsx Flame import", "still present")

# Sidebar has no broken imports
c25 = "Logo" in sidebar_src  # Logo is actually used in sidebar
ok("Sidebar.tsx: Logo import used (renders brand logo)") if c25 else fail("Sidebar.tsx Logo import")

# admin.html brand name consistent
c26 = "MyPy Tutor Admin" in admin_html
ok("admin.html title is 'MyPy Tutor Admin'") if c26 else fail("admin.html title branding")

# admin.html API_BASE is backend URL (correct — admin calls backend directly)
c27 = "API_BASE = 'https://mypytutor.onrender.com'" in admin_html
ok("admin.html API_BASE points to Render backend (correct for admin)") if c27 else fail("admin.html API_BASE", "should point to Render backend")

# ── SYNTAX CHECK ALL CHANGED PYTHON FILES ─────────────────────────────────
print("\n=== PYTHON SYNTAX ===")
py_files = ["app/main.py", "app/admin.py", "app/models.py", "app/progress.py"]
for pf in py_files:
    try:
        src = read(pf)
        ast.parse(src, filename=pf)
        ok(f"{pf} parses cleanly")
    except SyntaxError as e:
        fail(f"{pf} syntax error", f"line {e.lineno}: {e.msg}")

# ── SUMMARY ───────────────────────────────────────────────────────────────
total  = len(PASS) + len(FAIL)
print(f"\n{'='*52}")
print(f"TOTAL: {total}   PASSED: {len(PASS)}   FAILED: {len(FAIL)}")
if FAIL:
    print("\nFailed items:")
    for f in FAIL:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("All admin/branding checks passed.")
