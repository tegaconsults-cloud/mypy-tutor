"""Test /chat with an authenticated request to reproduce the 400."""
import urllib.request, urllib.error, json

BASE = "https://mypytutor.onrender.com"

def post(path, body, token=None):
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://mypytutor.com.ng",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"STATUS: {r.status}")
            print(f"CORS:   {r.headers.get('Access-Control-Allow-Origin','MISSING')}")
            body_out = json.loads(r.read())
            print(f"BODY:   {json.dumps(body_out, indent=2)[:400]}")
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:    body_out = json.dumps(json.loads(body_bytes), indent=2)
        except: body_out = body_bytes.decode()
        print(f"STATUS: {e.code}")
        print(f"CORS:   {e.headers.get('Access-Control-Allow-Origin','MISSING')}")
        print(f"BODY:   {body_out[:800]}")

# Test with the exact injected history pattern the frontend sends on first message
injected_system = (
    "You are Sir. Tega — Africa's Best AI Tech Tutor, created by Teamsamikoko Global Academy "
    "and built by TeamTega Technologies Limited, founded by Amb. Samuel Atulegwu Nwosu.\n\n"
    "STRICT BEHAVIOUR RULES — follow these on EVERY response without exception:\n"
    "1. EXPLAIN IN PLAIN WORDS FIRST. Never include Python code automatically.\n"
    "2. OFFER CODE AT THE END. After every explanation, ask: 'Would you like me to show you the Python code?'\n"
    "3. Be warm, encouraging, and expert. Teach step by step. Always introduce yourself fully on the very first message."
)

print("=== Test 1: Anonymous, no history ===")
post("/chat", {
    "message": "Hello",
    "history": [],
    "learner_id": "default",
    "level": "beginner",
    "conversation_id": None
})

print("\n=== Test 2: With injected assistant history (frontend first-message pattern) ===")
post("/chat", {
    "message": "What is a Python variable?",
    "history": [{"role": "assistant", "content": injected_system}],
    "learner_id": "test_abc123",
    "level": "beginner",
    "conversation_id": None
})

print("\n=== Test 3: Check /chat OPTIONS preflight ===")
req = urllib.request.Request(
    BASE + "/chat",
    headers={
        "Origin": "https://mypytutor.com.ng",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    },
    method="OPTIONS"
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"OPTIONS STATUS: {r.status}")
        print(f"CORS:  {r.headers.get('Access-Control-Allow-Origin','MISSING')}")
        print(f"METHODS: {r.headers.get('Access-Control-Allow-Methods','MISSING')}")
except urllib.error.HTTPError as e:
    print(f"OPTIONS {e.code}: {e.headers.get('Access-Control-Allow-Origin','MISSING')}")
