"""Test /chat endpoint and print exact error response."""
import urllib.request, urllib.error, json, sys

BASE = "https://mypytutor.onrender.com"

def post(path, body, token=None):
    headers = {"Content-Type": "application/json", "Origin": "https://mypytutor.com.ng"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp_body = json.loads(r.read())
            print(f"STATUS: {r.status}")
            print(f"CORS: {r.headers.get('Access-Control-Allow-Origin','MISSING')}")
            print(f"BODY: {json.dumps(resp_body, indent=2)[:500]}")
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            body_json = json.loads(body_bytes)
        except Exception:
            body_json = body_bytes.decode()[:500]
        print(f"STATUS: {e.code}")
        print(f"CORS: {e.headers.get('Access-Control-Allow-Origin','MISSING')}")
        print(f"BODY: {json.dumps(body_json, indent=2)[:800]}")

# Test 1: anonymous request (no token)
print("=== TEST 1: anonymous /chat ===")
post("/chat", {
    "message": "Hello Sir Tega",
    "history": [],
    "learner_id": "default",
    "level": "beginner",
    "conversation_id": None
})

# Test 2: with injected system message like frontend does
print("\n=== TEST 2: with injected assistant history (frontend pattern) ===")
injected = ("You are Sir. Tega — Africa's Best AI Tech Tutor. "
            "STRICT BEHAVIOUR RULES — follow these on EVERY response:\n"
            "1. EXPLAIN IN PLAIN WORDS FIRST. Never include Python code automatically.\n"
            "2. OFFER CODE AT THE END. After every explanation, ask: 'Would you like me to show you the Python code?'\n"
            "3. Be warm, encouraging, and expert. Teach step by step.")
post("/chat", {
    "message": "What is a variable?",
    "history": [{"role": "assistant", "content": injected}],
    "learner_id": "test_user_123",
    "level": "beginner",
    "conversation_id": None
})

# Test 3: with long conversation_id (potential 400 source)
print("\n=== TEST 3: long conversation_id ===")
post("/chat", {
    "message": "Hello",
    "history": [],
    "learner_id": "test_user_123",
    "level": "beginner",
    "conversation_id": "local_e_034a8980a7c2d8ab_abc123def456"
})
