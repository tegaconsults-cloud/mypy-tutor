"""Live test — quiz + assignment endpoints with all 3 LLM providers."""
import urllib.request, urllib.error, json, sys, time

BASE = "https://mypytutor.onrender.com"

def api(method, path, body=None, token=None, timeout=40):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type","")
            raw = r.read()
            return r.status, json.loads(raw) if "json" in ct else {"_text": raw.decode()[:300]}
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {"error": str(e)}
    except Exception as ex:
        return 0, {"error": str(ex)}

def show(label, status, data):
    ok = "✓" if 200 <= status < 300 else "✗"
    print(f"\n{ok} [{status}] {label}")
    for k, v in (data.items() if isinstance(data, dict) else []):
        val = str(v)[:200]
        if k in ("token",): val = "..."+val[-12:]
        print(f"     {k}: {val}")

# ── Auth ─────────────────────────────────────────────────────────────────
print("="*60)
print("SIGNING IN")
s, d = api("POST", "/auth/signin", {"email":"tegaconsults@gmail.com","password":"tegaconsults@gmail.com"})
show("SIGNIN", s, d)
TOKEN   = d.get("token", "")
LEARNER = d.get("learner_id", "")
if not TOKEN:
    print("ABORT: no token"); sys.exit(1)

# ── Quiz generate ─────────────────────────────────────────────────────────
print("\n"+"="*60)
print("QUIZ: generate question")
s, d = api("POST", "/quiz/generate", {
    "learner_id": LEARNER,
    "topic":      "Python lists",
    "level":      "beginner"
}, token=TOKEN)
show("QUIZ GENERATE", s, d)
QUESTION = d.get("question","")
OPTIONS  = d.get("options",[])
print(f"     question preview: {QUESTION[:100]}")
print(f"     options count:    {len(OPTIONS)}")
if OPTIONS:
    for o in OPTIONS: print(f"       {o}")

# ── Quiz answer — with correct_answer ─────────────────────────────────────
print("\n"+"="*60)
print("QUIZ: submit answer (correct_answer provided)")
# First option's letter
correct_letter = OPTIONS[0][0] if OPTIONS else "A"
s, d = api("POST", "/quiz/answer", {
    "learner_id":     LEARNER,
    "topic":          "Python lists",
    "level":          "beginner",
    "question":       QUESTION or "What is a Python list?",
    "answer":         OPTIONS[0] if OPTIONS else "A) An ordered collection",
    "correct_answer": correct_letter,
}, token=TOKEN)
show("QUIZ ANSWER", s, d)
print(f"     correct:     {d.get('correct')}")
print(f"     xp_gained:   {d.get('xp_gained')}")
print(f"     explanation: {str(d.get('explanation',''))[:150]}")

# ── Quiz answer — without correct_answer (LLM eval path) ─────────────────
print("\n"+"="*60)
print("QUIZ: submit answer (no correct_answer — LLM evaluation)")
s, d = api("POST", "/quiz/answer", {
    "learner_id":     LEARNER,
    "topic":          "Python lists",
    "level":          "beginner",
    "question":       "What method adds an item to the end of a list?",
    "answer":         "A) .append()",
    "correct_answer": "",
}, token=TOKEN)
show("QUIZ ANSWER (LLM eval)", s, d)
print(f"     correct: {d.get('correct')}")

# ── Quiz history ──────────────────────────────────────────────────────────
print("\n"+"="*60)
print("QUIZ: history")
s, d = api("GET", f"/history/{LEARNER}/quiz?limit=3", token=TOKEN)
show("QUIZ HISTORY", s, d)
attempts = d.get("attempts") or d.get("quiz_attempts") or []
print(f"     total attempts in response: {len(attempts)}")

# ── Assignment generate ───────────────────────────────────────────────────
print("\n"+"="*60)
print("ASSIGNMENT: generate")
s, d = api("POST", f"/assignments/generate?learner_id={LEARNER}&topic=Python%20functions", token=TOKEN)
show("ASSIGNMENT GENERATE", s, d)
AID     = d.get("assignment_id","")
CONTENT = d.get("content","")
print(f"     assignment_id: {AID}")
print(f"     content preview: {CONTENT[:150]}")

# ── Assignment list ───────────────────────────────────────────────────────
print("\n"+"="*60)
print("ASSIGNMENT: list")
s, d = api("GET", f"/assignments/{LEARNER}", token=TOKEN)
show("ASSIGNMENT LIST", s, d)
print(f"     total: {d.get('total')}")

# ── Assignment submit ─────────────────────────────────────────────────────
if AID:
    print("\n"+"="*60)
    print("ASSIGNMENT: submit")
    s, d = api("POST", f"/assignments/{AID}/submit", {
        "learner_id": LEARNER,
        "submission": "def add(a, b):\n    return a + b\n\nprint(add(2, 3))  # 5"
    }, token=TOKEN)
    show("ASSIGNMENT SUBMIT", s, d)

    # ── Assignment review (AI) ─────────────────────────────────────────────
    print("\n"+"="*60)
    print("ASSIGNMENT: AI review")
    s, d = api("POST", f"/assignments/{AID}/review?learner_id={LEARNER}", token=TOKEN, timeout=60)
    show("ASSIGNMENT REVIEW", s, d)
    print(f"     score:   {d.get('score')}")
    print(f"     feedback preview: {str(d.get('feedback',''))[:200]}")

print("\n"+"="*60)
print("ALL DONE\n")
