import urllib.request, urllib.error, json

url = "https://mypytutor.onrender.com/chat"
payload = json.dumps({
    "message": "Hello",
    "history": [],
    "learner_id": "default",
    "level": "beginner",
    "conversation_id": None
}).encode()

req = urllib.request.Request(url, data=payload, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("Origin", "https://mypytutor.com.ng")

try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print("STATUS:", r.status)
        print("CORS:", r.headers.get("Access-Control-Allow-Origin", "MISSING"))
        print("BODY:", r.read()[:300])
except urllib.error.HTTPError as e:
    print("STATUS:", e.code)
    print("CORS:", e.headers.get("Access-Control-Allow-Origin", "MISSING"))
    print("BODY:", e.read()[:600].decode())
except Exception as ex:
    print("EXCEPTION:", ex)
