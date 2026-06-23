"""
Admin dashboard — FastAPI router with Jinja2 server-side HTML rendering.
Pure Python: all pages rendered from Python string templates, no static HTML files.
Access at: /admin/
"""

import os, datetime, logging
from typing import Optional
from fastapi import APIRouter, Request, Form, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment

from app.admin import (
    verify_admin_login, create_admin_token, verify_admin_token,
    add_payment, confirm_payment, get_payments, get_revenue_summary,
    invite_team_member, create_task, update_task_status, get_team, get_tasks,
    get_certificates, log_certificate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# ── Jinja2 environment (no files — templates defined in Python) ──────────────
jinja = Environment(autoescape=True)

# ── Auth cookie helper ───────────────────────────────────────────────────────

def _get_admin_token(request: Request) -> Optional[str]:
    return request.cookies.get("mpt_admin")

def _require_admin(request: Request) -> str:
    token = _get_admin_token(request)
    if not token or not verify_admin_token(token):
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return token

def _redirect_login():
    return RedirectResponse("/admin/login", status_code=302)

# ── Base layout (Python string template) ────────────────────────────────────

BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Admin — {{ title }}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh}
a{color:#63b3ed;text-decoration:none}a:hover{text-decoration:underline}
.topbar{background:#1a202c;border-bottom:1px solid #2d3748;padding:12px 24px;display:flex;align-items:center;justify-content:space-between}
.topbar .logo{font-size:1rem;font-weight:700;color:#63b3ed}
.topbar .actions{display:flex;gap:10px;align-items:center;font-size:.82rem;color:#718096}
.topbar .logout{background:transparent;border:1px solid #2d3748;color:#718096;border-radius:6px;padding:5px 12px;font-size:.78rem;cursor:pointer;text-decoration:none}
.layout{display:flex;min-height:calc(100vh - 49px)}
.sidebar{width:200px;background:#1a202c;border-right:1px solid #2d3748;padding:14px 10px;flex-shrink:0}
.nav-link{display:block;padding:9px 14px;border-radius:8px;color:#718096;font-size:.84rem;margin-bottom:3px;transition:all .15s}
.nav-link:hover{background:#2d3748;color:#e2e8f0;text-decoration:none}
.nav-link.active{background:#2c5282;color:#90cdf4}
.main{flex:1;padding:24px;overflow-x:auto}
h2{color:#90cdf4;font-size:1.05rem;margin-bottom:16px}
h3{color:#e2e8f0;font-size:.92rem;margin-bottom:10px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}
.card{background:#1a202c;border:1px solid #2d3748;border-radius:10px;padding:14px}
.card .val{font-size:1.5rem;font-weight:800;color:#63b3ed}
.card .lbl{font-size:.7rem;color:#718096;margin-top:3px}
.card.g .val{color:#68d391}.card.gold .val{color:#f6ad55}.card.r .val{color:#fc8181}
.section{background:#1a202c;border:1px solid #2d3748;border-radius:10px;padding:16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:.83rem}
th{text-align:left;padding:7px 10px;color:#4a5568;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #2d3748}
td{padding:7px 10px;border-bottom:1px solid #1a202c;color:#a0aec0;vertical-align:top}
tr:hover td{background:#1a202c}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.67rem;font-weight:700}
.bg{background:#2c5282;color:#90cdf4}.gg{background:#276749;color:#68d391}
.gy{background:#744210;color:#f6ad55}.gr{background:#742a2a;color:#fc8181}.grey{background:#2d3748;color:#718096}
input,select,textarea{background:#0f1117;border:1px solid #2d3748;color:#e2e8f0;border-radius:7px;padding:8px 11px;font-size:.87rem;outline:none;font-family:inherit;transition:border-color .15s;width:100%}
input:focus,select:focus,textarea:focus{border-color:#4299e1}
textarea{min-height:70px;resize:vertical}
label{font-size:.76rem;color:#718096;display:block;margin-bottom:4px}
.form-row{margin-bottom:11px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.btn{display:inline-block;background:#3182ce;color:#fff;border:none;border-radius:7px;padding:9px 18px;font-size:.85rem;font-weight:600;cursor:pointer;transition:opacity .15s;text-decoration:none}
.btn:hover{opacity:.88;text-decoration:none;color:#fff}
.btn-sm{display:inline-block;background:#2c5282;color:#90cdf4;border:1px solid #4299e1;border-radius:6px;padding:4px 11px;font-size:.75rem;font-weight:600;cursor:pointer;text-decoration:none}
.btn-sm:hover{opacity:.88;text-decoration:none}
.btn-g{background:#276749;color:#68d391;border:1px solid #2f855a}
.btn-r{background:#742a2a;color:#fc8181;border:1px solid #9b2c2c}
.alert{padding:10px 14px;border-radius:8px;font-size:.84rem;margin-bottom:14px}
.alert-g{background:#1c3a26;border:1px solid #276749;color:#68d391}
.alert-r{background:#3b1a1a;border:1px solid #742a2a;color:#fc8181}
.msg-box{background:#1a365d;border:1px solid #2c5282;border-radius:8px;padding:11px 14px;font-size:.83rem;color:#90cdf4;margin-bottom:14px}
@media(max-width:640px){.layout{flex-direction:column}.sidebar{width:100%;display:flex;flex-wrap:wrap;padding:8px}.nav-link{flex:1;min-width:70px;text-align:center;padding:7px 6px;font-size:.75rem}.grid2{grid-template-columns:1fr}.main{padding:14px}}
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">🐍 MyPy Tutor Admin</span>
  <div class="actions">
    <span>{{ admin_email }}</span>
    <a href="/admin/logout" class="logout">Sign Out</a>
  </div>
</div>
<div class="layout">
  <nav class="sidebar">
    <a href="/admin/" class="nav-link {{ 'active' if page=='dashboard' else '' }}">📊 Dashboard</a>
    <a href="/admin/users" class="nav-link {{ 'active' if page=='users' else '' }}">👥 Users</a>
    <a href="/admin/activity" class="nav-link {{ 'active' if page=='activity' else '' }}">🔍 Activity</a>
    <a href="/admin/payments" class="nav-link {{ 'active' if page=='payments' else '' }}">💳 Payments</a>
    <a href="/admin/certificates" class="nav-link {{ 'active' if page=='certificates' else '' }}">🎓 Certificates</a>
    <a href="/admin/feedback" class="nav-link {{ 'active' if page=='feedback' else '' }}">💬 Feedback</a>
    <a href="/admin/announcements" class="nav-link {{ 'active' if page=='announcements' else '' }}">📢 Announce</a>
    <a href="/admin/team" class="nav-link {{ 'active' if page=='team' else '' }}">👨‍💼 Team</a>
    <a href="/admin/tasks" class="nav-link {{ 'active' if page=='tasks' else '' }}">📋 Tasks</a>
    <a href="/admin/files" class="nav-link {{ 'active' if page=='files' else '' }}">📁 Files</a>
  </nav>
  <main class="main">
    {% if msg %}<div class="alert alert-g">{{ msg }}</div>{% endif %}
    {% if err %}<div class="alert alert-r">{{ err }}</div>{% endif %}
    {{ content }}
  </main>
</div>
</body>
</html>"""

def render(template_str: str, **ctx) -> str:
    admin_email = os.getenv("ADMIN_EMAIL", "admin")
    t = jinja.from_string(BASE)
    content = jinja.from_string(template_str).render(**ctx)
    return t.render(content=content, admin_email=admin_email, **ctx)

def html(body: str, **ctx) -> HTMLResponse:
    return HTMLResponse(render(body, **ctx))

# ── Login / Logout ───────────────────────────────────────────────────────────

LOGIN_PAGE = """
<div style="display:flex;align-items:center;justify-content:center;min-height:calc(100vh - 100px)">
<div style="background:#1a202c;border:1px solid #2d3748;border-radius:14px;padding:36px 32px;width:100%;max-width:380px">
  <h2 style="text-align:center;margin-bottom:4px">Admin Sign In</h2>
  <p style="font-size:.82rem;color:#718096;text-align:center;margin-bottom:20px">MyPy Tutor — Teamsamikoko Global Academy</p>
  <form method="post" action="/admin/login">
    <div class="form-row"><label>Admin Email</label><input name="email" type="email" required autocomplete="email"/></div>
    <div class="form-row"><label>Password</label><input name="password" type="password" required autocomplete="current-password"/></div>
    <button type="submit" class="btn" style="width:100%;margin-top:4px">Sign In</button>
  </form>
</div></div>"""

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, err: str = ""):
    token = _get_admin_token(request)
    if token and verify_admin_token(token):
        return RedirectResponse("/admin/", status_code=302)
    t = jinja.from_string("""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>Admin Login</title>
    <style>*{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .box{background:#1a202c;border:1px solid #2d3748;border-radius:14px;padding:36px 32px;width:100%;max-width:380px}
    h2{color:#63b3ed;text-align:center;margin-bottom:4px;font-size:1.1rem}
    p{font-size:.82rem;color:#718096;text-align:center;margin-bottom:20px}
    label{font-size:.76rem;color:#718096;display:block;margin-bottom:4px}
    input{background:#0f1117;border:1px solid #2d3748;color:#e2e8f0;border-radius:7px;padding:10px 12px;font-size:.9rem;outline:none;width:100%;margin-bottom:12px}
    input:focus{border-color:#4299e1}
    button{width:100%;background:#3182ce;color:#fff;border:none;border-radius:8px;padding:12px;font-size:.92rem;font-weight:700;cursor:pointer}
    .err{background:#3b1a1a;border:1px solid #742a2a;color:#fc8181;border-radius:7px;padding:9px 12px;font-size:.82rem;margin-bottom:12px}
    </style></head><body>
    <div class="box">
      <h2>🐍 MyPy Tutor Admin</h2>
      <p>Sign in with your admin credentials</p>
      {% if err %}<div class="err">{{ err }}</div>{% endif %}
      <form method="post" action="/admin/login">
        <label>Admin Email</label><input name="email" type="email" required autocomplete="email" value="{{ email }}"/>
        <label>Password</label><input name="password" type="password" required autocomplete="current-password"/>
        <button type="submit">Sign In</button>
      </form>
    </div></body></html>""")
    return HTMLResponse(t.render(err=err, email=""))

@router.post("/login")
async def admin_login_post(email: str = Form(...), password: str = Form(...)):
    if verify_admin_login(email, password):
        token = create_admin_token()
        resp = RedirectResponse("/admin/", status_code=302)
        resp.set_cookie("mpt_admin", token, max_age=3600*8, httponly=True, samesite="lax")
        return resp
    return RedirectResponse("/admin/login?err=Invalid+credentials", status_code=302)

@router.get("/logout")
async def admin_logout():
    resp = RedirectResponse("/admin/login", status_code=302)
    resp.delete_cookie("mpt_admin")
    return resp

# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, msg: str = "", err: str = ""):
    _require_admin(request)
    from app.progress import _store as ls
    from app.feedback import get_summary
    from app.security import _daily_prompt_store
    today = datetime.date.today().isoformat()
    active = sum(1 for d,c in _daily_prompt_store.values() if d==today and c>0)
    rev = get_revenue_summary()
    fb  = get_summary()
    certs = get_certificates()
    tasks = get_tasks()
    tiers = {t: sum(1 for p in ls.values() if p.tier==t) for t in ['free','tier1','tier2','tier3']}
    body = """
<h2>📊 Dashboard</h2>
<div class="cards">
  <div class="card"><div class="val">{{total_users}}</div><div class="lbl">Total Users</div></div>
  <div class="card g"><div class="val">{{active}}</div><div class="lbl">Active Today</div></div>
  <div class="card gold"><div class="val">₦{{revenue}}</div><div class="lbl">Total Revenue</div></div>
  <div class="card"><div class="val">{{payments}}</div><div class="lbl">Payments</div></div>
  <div class="card"><div class="val">{{certs}}</div><div class="lbl">Certificates</div></div>
  <div class="card"><div class="val">{{open_tasks}}</div><div class="lbl">Open Tasks</div></div>
  <div class="card g"><div class="val">{{sat}}%</div><div class="lbl">Satisfaction</div></div>
  <div class="card"><div class="val">{{surveys}}</div><div class="lbl">Surveys</div></div>
</div>
<div class="grid2">
  <div class="section"><h3>User Tiers</h3>
    {% for tier,count in tiers.items() %}
    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #2d3748;font-size:.84rem">
      <span class="badge {{'gy' if tier=='tier2' else 'bg' if tier=='tier1' else 'gr' if tier=='tier3' else 'grey'}}">{{tier}}</span>
      <strong>{{count}} users</strong>
    </div>{% endfor %}
  </div>
  <div class="section"><h3>Revenue by Plan</h3>
    {% for plan,amt in by_plan.items() %}
    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #2d3748;font-size:.84rem">
      <span>{{plan}}</span><strong style="color:#68d391">₦{{"{:,.0f}".format(amt)}}</strong>
    </div>{% endfor %}
    {% if not by_plan %}<span style="color:#4a5568;font-size:.83rem">No payments yet.</span>{% endif %}
  </div>
</div>
<div class="section"><h3>Quick Links</h3>
  <div style="display:flex;flex-wrap:wrap;gap:8px">
    <a href="/admin/users" class="btn-sm">👥 Manage Users</a>
    <a href="/admin/payments" class="btn-sm">💳 Payments</a>
    <a href="/admin/certificates" class="btn-sm">🎓 Certificates</a>
    <a href="/admin/announcements" class="btn-sm">📢 Send Announcement</a>
    <a href="/admin/tasks" class="btn-sm">📋 Tasks</a>
  </div>
</div>"""
    t = jinja.from_string(body)
    content = t.render(total_users=len(ls), active=active,
        revenue="{:,.0f}".format(rev['total_revenue']),
        payments=rev['total_payments'], certs=len(certs),
        open_tasks=sum(1 for t2 in tasks if t2.status=='open'),
        sat=fb.satisfaction_pct, surveys=fb.total_surveys,
        tiers=tiers, by_plan=rev.get('by_plan',{}))
    return HTMLResponse(render(content, page="dashboard", title="Dashboard", msg=msg, err=err))

# ── Users ────────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, msg: str = "", err: str = ""):
    _require_admin(request)
    from app.progress import _store as ls
    from app.email_auth import _confirmed
    rows = ""
    for lid, p in ls.items():
        tier_cls = {"free":"grey","tier1":"bg","tier2":"gy","tier3":"gr"}.get(p.tier,"grey")
        terminate_link = f"/admin/users/{lid}/terminate"
        profile_link   = f"/admin/users/{lid}"
        rows += (
            f"<tr><td style='font-size:.75rem;color:#4a5568'>{lid}</td>"
            f"<td><span class='badge {tier_cls}'>{p.tier}</span></td>"
            f"<td>{p.level}</td><td>{p.xp}</td>"
            f"<td>{len(p.topics_seen)}</td><td>{len(p.completed_projects)}</td>"
            f"<td><a href='{profile_link}' class='btn-sm'>View</a> "
            f"<a href='{terminate_link}' class='btn-sm btn-r'>Terminate</a></td></tr>"
        )
    email_rows = ""
    for e, u in _confirmed.items():
        uname = u['name']
        email_rows += f"<tr><td>{e}</td><td>{uname}</td><td>email</td><td>confirmed</td></tr>"
    
    body = f"""<h2>👥 Users ({len(ls)} profiles · {len(_confirmed)} email accounts)</h2>
    <div class="section"><h3>Learner Profiles</h3>
    <div style="overflow-x:auto"><table><thead><tr>
    <th>ID</th><th>Tier</th><th>Level</th><th>XP</th><th>Topics</th><th>Courses</th><th>Actions</th>
    </tr></thead><tbody>{rows or '<tr><td colspan="7" style="color:#4a5568">No users yet.</td></tr>'}</tbody></table></div></div>
    <div class="section"><h3>Email Accounts</h3>
    <div style="overflow-x:auto"><table><thead><tr><th>Email</th><th>Name</th><th>Type</th><th>Status</th></tr></thead>
    <tbody>{email_rows or '<tr><td colspan="4" style="color:#4a5568">None yet.</td></tr>'}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="users", title="Users", msg=msg, err=err))


@router.get("/users/{learner_id}", response_class=HTMLResponse)
async def admin_user_detail(learner_id: str, request: Request):
    _require_admin(request)
    from app.progress import _store as ls
    from app.security import _daily_prompt_store
    p = ls.get(learner_id)
    if not p:
        return HTMLResponse(render("<h2>User not found</h2>", page="users", title="User", msg="", err=""))
    today = datetime.date.today().isoformat()
    prompts_today = _daily_prompt_store.get(learner_id, (None,0))[1]
    topics_html = ""
    for t, tp in p.topic_progress.items():
        status_badge = '<span class="badge gr">gap</span>' if tp.weak else '<span class="badge gg">ok</span>'
        topics_html += (
            f"<tr><td>{t}</td><td>{tp.lessons_completed}</td>"
            f"<td>{tp.exercises_passed}/{tp.exercises_attempted}</td>"
            f"<td>{status_badge}</td></tr>"
        )
    tier_cls = {"free":"grey","tier1":"bg","tier2":"gy","tier3":"gr"}.get(p.tier,"grey")
    body = f"""<h2>👤 User: {learner_id}</h2>
    <div class="grid2">
    <div class="section"><h3>Profile</h3>
      <div style="font-size:.86rem;line-height:2">
        <b>Tier:</b> <span class="badge {tier_cls}">{p.tier}</span><br>
        <b>Level:</b> {p.level}<br><b>XP:</b> {p.xp}<br>
        <b>Badges:</b> {', '.join(p.badges) or '—'}<br>
        <b>Prompts today:</b> {prompts_today}<br>
        <b>Courses done:</b> {len(p.completed_projects)}<br>
        <b>Current course:</b> {p.current_course or '—'} (step {p.current_course_step})<br>
      </div>
    </div>
    <div class="section"><h3>Actions</h3>
      <form method="post" action="/admin/users/{learner_id}/set-tier" style="margin-bottom:12px">
        <div class="form-row"><label>Set Tier</label>
        <select name="tier"><option value="free">Free</option><option value="tier1">Tier 1</option>
        <option value="tier2">Tier 2</option><option value="tier3">Tier 3</option></select></div>
        <button class="btn" type="submit">Update Tier</button>
      </form>
      <a href="/admin/users/{learner_id}/terminate" class="btn btn-r"
         onclick="return confirm('Terminate subscription for {learner_id}?')">🚫 Terminate Subscription</a>
    </div></div>
    <div class="section"><h3>Topic Progress</h3>
    <div style="overflow-x:auto"><table><thead><tr><th>Topic</th><th>Lessons</th><th>Exercises</th><th>Status</th></tr></thead>
    <tbody>{topics_html or '<tr><td colspan="4" style="color:#4a5568">No topic data.</td></tr>'}</tbody></table></div></div>
    <p style="margin-top:12px"><a href="/admin/users" class="btn-sm">← Back to Users</a></p>"""
    return HTMLResponse(render(body, page="users", title=f"User {learner_id}", msg="", err=""))


@router.post("/users/{learner_id}/set-tier")
async def admin_set_tier(learner_id: str, request: Request, tier: str = Form(...)):
    _require_admin(request)
    from app.progress import _store as ls, save_profile
    p = ls.get(learner_id)
    if p:
        p.tier = tier
        save_profile(p)
    return RedirectResponse(f"/admin/users/{learner_id}?msg=Tier+updated+to+{tier}", status_code=302)


@router.get("/users/{learner_id}/terminate")
async def admin_terminate(learner_id: str, request: Request):
    _require_admin(request)
    from app.progress import _store as ls, save_profile
    p = ls.get(learner_id)
    if p:
        p.tier = "free"
        p.current_course = None
        p.current_course_step = 0
        save_profile(p)
    return RedirectResponse(f"/admin/users?msg=Subscription+terminated+for+{learner_id}", status_code=302)

# ── Activity Monitor ─────────────────────────────────────────────────────────

from app.admin import _activity_log  # defined below — track what users do

@router.get("/activity", response_class=HTMLResponse)
async def admin_activity(request: Request):
    _require_admin(request)
    from app.admin import _activity_log
    rows = "".join(
        f"<tr><td style='font-size:.75rem;color:#4a5568'>{a['ts']}</td>"
        f"<td>{a['learner_id']}</td><td>{a['action']}</td>"
        f"<td style='max-width:300px;word-break:break-word'>{a['detail']}</td></tr>"
        for a in reversed(_activity_log[-200:])
    )
    body = f"""<h2>🔍 User Activity Monitor</h2>
    <div class="section">
    <p style="font-size:.82rem;color:#718096;margin-bottom:12px">Last 200 actions across all users</p>
    <div style="overflow-x:auto"><table><thead><tr>
    <th>Time</th><th>User</th><th>Action</th><th>Detail</th>
    </tr></thead><tbody>{rows or '<tr><td colspan="4" style="color:#4a5568">No activity yet.</td></tr>'}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="activity", title="Activity", msg="", err=""))


# ── Payments ─────────────────────────────────────────────────────────────────

@router.get("/payments", response_class=HTMLResponse)
async def admin_payments_page(request: Request, msg: str = "", err: str = ""):
    _require_admin(request)
    rev = get_revenue_summary()
    pmts = get_payments()
    rows = ""
    for p in pmts:
        status_cls = "gg" if p.status == "confirmed" else "gy" if p.status == "pending" else "gr"
        date_str   = datetime.datetime.fromtimestamp(p.created_at).strftime('%Y-%m-%d')
        confirm_btn = f"<a href='/admin/payments/{p.id}/confirm' class='btn-sm btn-g'>Confirm</a>" if p.status == "pending" else ""
        rows += (
            f"<tr><td>{p.id}</td>"
            f"<td>{p.user_name}<br><span style='font-size:.72rem;color:#4a5568'>{p.user_email}</span></td>"
            f"<td>&#8358;{p.amount:,.0f}</td><td>{p.plan}</td><td>{p.method}</td>"
            f"<td><span class='badge {status_cls}'>{p.status}</span></td>"
            f"<td>{date_str}</td><td>{confirm_btn}</td></tr>"
        )
    body = f"""<h2>💳 Payments</h2>
    <div class="cards">
      <div class="card gold"><div class="val">₦{rev['total_revenue']:,.0f}</div><div class="lbl">Total Revenue</div></div>
      <div class="card g"><div class="val">{rev['confirmed']}</div><div class="lbl">Confirmed</div></div>
      <div class="card"><div class="val">{rev['pending']}</div><div class="lbl">Pending</div></div>
    </div>
    <div class="section"><h3>Record New Payment</h3>
    <form method="post" action="/admin/payments/add">
    <div class="grid2">
      <div class="form-row"><label>User Email</label><input name="user_email" placeholder="user@email.com" required/></div>
      <div class="form-row"><label>User Name</label><input name="user_name" placeholder="Full name" required/></div>
      <div class="form-row"><label>Amount (₦)</label><input name="amount" type="number" placeholder="5000" required/></div>
      <div class="form-row"><label>Plan</label><select name="plan">
        <option value="tier1">Tier 1 — ₦5,000/mo</option>
        <option value="tier2">Tier 2 — ₦10,000/mo</option>
        <option value="tier3">Tier 3 — ₦20,000/mo</option>
        <option value="basic-cert">Basic Certificate — ₦30,000</option>
        <option value="adv-cert">Advanced Certificate — ₦50,000</option>
        <option value="exec-cert">Executive Masters — ₦80,000</option>
      </select></div>
      <div class="form-row"><label>Method</label><select name="method">
        <option value="bank">Bank Transfer</option><option value="paystack">Paystack</option></select></div>
      <div class="form-row"><label>Notes</label><input name="notes" placeholder="Optional"/></div>
    </div>
    <button class="btn" type="submit">+ Record Payment</button>
    </form></div>
    <div class="section"><h3>All Payments</h3>
    <div style="overflow-x:auto"><table><thead><tr>
    <th>ID</th><th>User</th><th>Amount</th><th>Plan</th><th>Method</th><th>Status</th><th>Date</th><th></th>
    </tr></thead><tbody>{rows or '<tr><td colspan="8" style="color:#4a5568">No payments yet.</td></tr>'}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="payments", title="Payments", msg=msg, err=err))

@router.post("/payments/add")
async def admin_add_payment_post(request: Request, user_email: str=Form(...),
    user_name: str=Form(...), amount: float=Form(...), plan: str=Form(...),
    method: str=Form("bank"), notes: str=Form("")):
    _require_admin(request)
    p = add_payment(user_email, user_name, amount, plan, method, notes)
    return RedirectResponse(f"/admin/payments?msg=Payment+{p.id}+recorded", status_code=302)

@router.get("/payments/{payment_id}/confirm")
async def admin_confirm_payment_get(payment_id: str, request: Request):
    _require_admin(request)
    confirm_payment(payment_id)
    return RedirectResponse(f"/admin/payments?msg=Payment+{payment_id}+confirmed", status_code=302)

# ── Certificates ─────────────────────────────────────────────────────────────

@router.get("/certificates", response_class=HTMLResponse)
async def admin_certs_page(request: Request, msg: str = ""):
    _require_admin(request)
    certs = get_certificates()
    rows = ""
    for c in certs:
        level_cls = "gr" if c.level == "executive" else "gy" if c.level == "advanced" else "gg"
        view_url = f"/certificate/{c.level}?name={c.learner_name}&learner_id={c.learner_id}"
        issued = datetime.datetime.fromtimestamp(c.issued_at).strftime('%Y-%m-%d %H:%M')
        rows += (
            f"<tr><td>{c.cert_id}</td><td>{c.learner_name}</td><td>{c.learner_id}</td>"
            f"<td><span class='badge {level_cls}'>{c.level}</span></td>"
            f"<td>{issued}</td>"
            f"<td><a href='{view_url}' target='_blank' class='btn-sm'>View PDF</a></td></tr>"
        )
    body = f"""<h2>🎓 Certificates Issued ({len(certs)})</h2>
    <div class="section">
    <div style="overflow-x:auto"><table><thead><tr>
    <th>Cert ID</th><th>Name</th><th>Learner ID</th><th>Level</th><th>Issued</th><th></th>
    </tr></thead><tbody>{rows or '<tr><td colspan="6" style="color:#4a5568">No certificates issued yet.</td></tr>'}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="certificates", title="Certificates", msg=msg, err=""))


# ── Feedback ─────────────────────────────────────────────────────────────────

@router.get("/feedback", response_class=HTMLResponse)
async def admin_feedback_page(request: Request):
    _require_admin(request)
    from app.feedback import _ratings, _surveys, get_summary
    s = get_summary()
    ratings_html = ""
    for r in list(reversed(_ratings))[:50]:
        thumb = "👍" if r.rating == "up" else "👎"
        topic_s = r.topic or "—"
        comment_s = r.comment or "—"
        ratings_html += f"<tr><td>{thumb}</td><td>{r.learner_id}</td><td>{topic_s}</td><td>{comment_s}</td></tr>"
    
    surveys_html = ""
    for sv in list(reversed(_surveys))[:30]:
        stars = "⭐" * sv.overall
        rec = "✅" if sv.would_recommend else "❌"
        sug = sv.suggestion or "—"
        surveys_html += f"<tr><td>{stars}</td><td>{sv.learner_id}</td><td>{sv.clarity}/5</td><td>{sv.helpfulness}/5</td><td>{rec}</td><td style='max-width:240px'>{sug}</td></tr>"
    
    body = f"""<h2>💬 User Feedback</h2>
    <div class="cards">
      <div class="card g"><div class="val">{s.satisfaction_pct}%</div><div class="lbl">Satisfaction</div></div>
      <div class="card"><div class="val">{s.total_ratings}</div><div class="lbl">Ratings</div></div>
      <div class="card"><div class="val">{s.avg_overall}</div><div class="lbl">Avg Overall</div></div>
      <div class="card"><div class="val">{s.avg_clarity}</div><div class="lbl">Avg Clarity</div></div>
      <div class="card"><div class="val">{s.avg_helpfulness}</div><div class="lbl">Avg Helpfulness</div></div>
      <div class="card"><div class="val">{s.total_surveys}</div><div class="lbl">Surveys</div></div>
    </div>
    <div class="section"><h3>Recent Ratings</h3>
    <table><thead><tr><th></th><th>User</th><th>Topic</th><th>Comment</th></tr></thead>
    <tbody>{ratings_html or '<tr><td colspan="4" style="color:#4a5568">No ratings yet.</td></tr>'}</tbody></table></div>
    <div class="section"><h3>Survey Responses</h3>
    <div style="overflow-x:auto"><table><thead><tr><th>Overall</th><th>User</th><th>Clarity</th><th>Helpful</th><th>Recommend</th><th>Suggestion</th></tr></thead>
    <tbody>{surveys_html or '<tr><td colspan="6" style="color:#4a5568">No surveys yet.</td></tr>'}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="feedback", title="Feedback", msg="", err=""))


# ── Announcements ─────────────────────────────────────────────────────────────

@router.get("/announcements", response_class=HTMLResponse)
async def admin_announcements_page(request: Request, msg: str = "", err: str = ""):
    _require_admin(request)
    from app.admin import _announcements
    rows = ""
    for a in reversed(_announcements):
        adate = datetime.datetime.fromisoformat(a['sent_at']).strftime('%Y-%m-%d %H:%M')
        rows += f"<tr><td>{a['subject']}</td><td>{a['target']}</td><td>{a['sent_to']} users</td><td>{adate}</td></tr>"
    
    body = f"""<h2>📢 Announcements</h2>
    <div class="section"><h3>Send Announcement to All Users</h3>
    <form method="post" action="/admin/announcements/send">
      <div class="form-row"><label>Target</label><select name="target">
        <option value="all">All Users</option>
        <option value="free">Free Plan Only</option>
        <option value="tier1">Tier 1 Only</option>
        <option value="tier2">Tier 2 Only</option>
        <option value="tier3">Tier 3 Only</option>
        <option value="paid">All Paid Users</option>
      </select></div>
      <div class="form-row"><label>Subject</label><input name="subject" placeholder="e.g. New features now live!" required/></div>
      <div class="form-row"><label>Message (HTML supported)</label>
        <textarea name="body_text" rows="5" placeholder="Write your announcement here..."></textarea></div>
      <button class="btn" type="submit">📢 Send Announcement</button>
    </form></div>
    <div class="section"><h3>Sent Announcements</h3>
    <table><thead><tr><th>Subject</th><th>Target</th><th>Sent To</th><th>Date</th></tr></thead>
    <tbody>{rows or '<tr><td colspan="4" style="color:#4a5568">No announcements sent yet.</td></tr>'}</tbody></table></div>"""
    return HTMLResponse(render(body, page="announcements", title="Announcements", msg=msg, err=err))

@router.post("/announcements/send")
async def admin_send_announcement(request: Request, target: str=Form(...),
    subject: str=Form(...), body_text: str=Form(...)):
    _require_admin(request)
    from app.admin import send_announcement
    sent = await send_announcement(target, subject, body_text)
    return RedirectResponse(f"/admin/announcements?msg=Sent+to+{sent}+users", status_code=302)

# ── Team ─────────────────────────────────────────────────────────────────────

@router.get("/team", response_class=HTMLResponse)
async def admin_team_page(request: Request, msg: str = "", err: str = ""):
    _require_admin(request)
    members = get_team()
    rows = ""
    for m in members:
        sc = "gg" if m.status == "active" else "gy"
        rows += f"<tr><td>{m.name}</td><td>{m.email}</td><td><span class='badge bg'>{m.role}</span></td><td><span class='badge {sc}'>{m.status}</span></td></tr>"
    
    body = f"""<h2>👨‍💼 Team Members ({len(members)})</h2>
    <div class="grid2">
    <div class="section"><h3>Invite Team Member</h3>
    <form method="post" action="/admin/team/invite">
      <div class="form-row"><label>Email</label><input name="email" type="email" required placeholder="member@email.com"/></div>
      <div class="form-row"><label>Full Name</label><input name="name" required placeholder="Full name"/></div>
      <div class="form-row"><label>Role</label><select name="role">
        <option value="team">Team Member</option><option value="tutor">Tutor</option>
        <option value="support">Support</option><option value="dev">Developer</option></select></div>
      <button class="btn" type="submit">Send Invite</button>
    </form></div>
    <div class="section"><h3>Current Team</h3>
    <table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead>
    <tbody>{rows or '<tr><td colspan="4" style="color:#4a5568">No team members yet.</td></tr>'}</tbody></table></div>
    </div>"""
    return HTMLResponse(render(body, page="team", title="Team", msg=msg, err=err))

@router.post("/team/invite")
async def admin_invite_post(request: Request, email: str=Form(...), name: str=Form(...), role: str=Form("team")):
    _require_admin(request)
    invite_team_member(email, name, role)
    try:
        from app.email_auth import _send_email, APP_URL
        html_body = f"""<div style="font-family:Arial;background:#0f1117;color:#e2e8f0;padding:32px">
        <h2 style="color:#63b3ed">🐍 MyPy Tutor — Team Invitation</h2>
        <p>Hi {name}, you've been invited to join the MyPy Tutor team as <strong>{role}</strong>.</p>
        <a href="{APP_URL}/admin/login" style="background:#3182ce;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">Access Admin</a>
        </div>"""
        _send_email(email, "You're invited to the MyPy Tutor team!", html_body,
                    f"Hi {name}, you've been invited to the MyPy Tutor team as {role}.")
    except Exception as e:
        logger.warning("Team invite email error: %s", e)
    return RedirectResponse(f"/admin/team?msg=Invited+{email}", status_code=302)


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/tasks", response_class=HTMLResponse)
async def admin_tasks_page(request: Request, msg: str = "", err: str = ""):
    _require_admin(request)
    tasks = get_tasks()
    priority_cls = {"urgent":"gr","high":"gy","medium":"bg","low":"grey"}
    status_cls   = {"open":"gy","in_progress":"bg","done":"gg"}
    rows = ""
    for t in tasks:
        pc = priority_cls.get(t.priority, "grey")
        sc = status_cls.get(t.status, "grey")
        desc_short = t.description[:60] + ("..." if len(t.description) > 60 else "")
        progress_btn = f"<a href='/admin/tasks/{t.id}/progress' class='btn-sm'>▶</a> " if t.status == "open" else ""
        done_btn     = f"<a href='/admin/tasks/{t.id}/done' class='btn-sm btn-g'>✓</a>" if t.status != "done" else ""
        rows += (
            f"<tr><td>{t.id}</td>"
            f"<td><strong>{t.title}</strong><br>"
            f"<span style='font-size:.75rem;color:#718096'>{desc_short}</span></td>"
            f"<td>{t.assigned_to}</td>"
            f"<td><span class='badge {pc}'>{t.priority}</span></td>"
            f"<td><span class='badge {sc}'>{t.status}</span></td>"
            f"<td>{t.due_date or '—'}</td>"
            f"<td style='white-space:nowrap'>{progress_btn}{done_btn}</td></tr>"
        )
    members = get_team()
    member_opts = ""
    for m in members:
        member_opts += f"<option value='{m.email}'>{m.name} ({m.email})</option>"
    
    body = f"""<h2>📋 Tasks</h2>
    <div class="section"><h3>Create New Task</h3>
    <form method="post" action="/admin/tasks/create">
    <div class="grid2">
      <div class="form-row"><label>Title</label><input name="title" required placeholder="Task title"/></div>
      <div class="form-row"><label>Assign To</label>
        <select name="assigned_to"><option value="">— Select team member —</option>{member_opts}</select>
        <input name="assigned_to_custom" placeholder="Or type email directly" style="margin-top:6px"/></div>
      <div class="form-row"><label>Priority</label><select name="priority">
        <option value="low">Low</option><option value="medium" selected>Medium</option>
        <option value="high">High</option><option value="urgent">Urgent</option></select></div>
      <div class="form-row"><label>Due Date</label><input name="due_date" type="date"/></div>
    </div>
    <div class="form-row"><label>Description</label><textarea name="description" rows="3" placeholder="Task details..."></textarea></div>
    <button class="btn" type="submit">Assign Task</button>
    </form></div>
    <div class="section"><h3>All Tasks ({len(tasks)})</h3>
    <div style="overflow-x:auto"><table><thead><tr>
    <th>ID</th><th>Task</th><th>Assigned To</th><th>Priority</th><th>Status</th><th>Due</th><th></th>
    </tr></thead><tbody>{rows or '<tr><td colspan="7" style="color:#4a5568">No tasks yet.</td></tr>'}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="tasks", title="Tasks", msg=msg, err=err))

@router.post("/tasks/create")
async def admin_create_task_post(request: Request, title: str=Form(...), description: str=Form(""),
    assigned_to: str=Form(""), assigned_to_custom: str=Form(""), priority: str=Form("medium"), due_date: str=Form("")):
    _require_admin(request)
    assignee = assigned_to_custom.strip() or assigned_to.strip()
    if not assignee:
        return RedirectResponse("/admin/tasks?err=Assignee+required", status_code=302)
    t = create_task(title, description, assignee, priority, due_date)
    try:
        from app.email_auth import _send_email, APP_URL
        html_body = f"""<div style="font-family:Arial;background:#0f1117;color:#e2e8f0;padding:32px">
        <h2 style="color:#f6ad55">📋 New Task: {title}</h2>
        <p>{description}</p><p>Priority: <strong>{priority.upper()}</strong></p>
        {f'<p>Due: {due_date}</p>' if due_date else ''}
        <a href="{APP_URL}/admin/tasks" style="background:#3182ce;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">View Tasks</a>
        </div>"""
        _send_email(assignee, f"New task assigned: {title}", html_body, f"Task: {title}\n{description}")
    except Exception as e:
        logger.warning("Task email error: %s", e)
    return RedirectResponse(f"/admin/tasks?msg=Task+{t.id}+assigned", status_code=302)

@router.get("/tasks/{task_id}/progress")
async def task_to_progress(task_id: str, request: Request):
    _require_admin(request)
    update_task_status(task_id, "in_progress")
    return RedirectResponse("/admin/tasks?msg=Task+marked+in+progress", status_code=302)

@router.get("/tasks/{task_id}/done")
async def task_to_done(task_id: str, request: Request):
    _require_admin(request)
    update_task_status(task_id, "done")
    return RedirectResponse("/admin/tasks?msg=Task+marked+done", status_code=302)


# ── Files ─────────────────────────────────────────────────────────────────────

@router.get("/files", response_class=HTMLResponse)
async def admin_files_page(request: Request):
    _require_admin(request)
    import os as _os
    app_files = []
    for root, dirs, files in _os.walk("."):
        dirs[:] = [d for d in dirs if d not in ['.venv','__pycache__','.git','.hypothesis','node_modules']]
        for f in files:
            path = _os.path.join(root, f).replace("\\","/").lstrip("./")
            size = _os.path.getsize(_os.path.join(root, f))
            app_files.append((path, size))
    app_files.sort(key=lambda x: x[0])
    rows = "".join(
        f"<tr><td style='font-family:monospace;font-size:.78rem'>{p}</td>"
        f"<td style='text-align:right;font-size:.78rem;color:#718096'>{s:,} B</td></tr>"
        for p,s in app_files if any(p.startswith(d) for d in ['app/','static/','requirements'])
    )
    body = f"""<h2>📁 Project Files</h2>
    <div class="section">
    <p style="font-size:.82rem;color:#718096;margin-bottom:12px">All app and static files deployed on Render. {len(app_files)} files total.</p>
    <div style="overflow-x:auto"><table><thead><tr><th>Path</th><th style="text-align:right">Size</th></tr></thead>
    <tbody>{rows}</tbody></table></div></div>"""
    return HTMLResponse(render(body, page="files", title="Files", msg="", err=""))
