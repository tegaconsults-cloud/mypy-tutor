import urllib.request, urllib.error, json

url = "https://mypytutor.onrender.com/chat"
body = json.dumps({"message": "hello", "learner_id": "test123", "level": "beginner", "history": []}).encode()
req = urllib.request.Request(url, data=body, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("Origin", "https://mypytutor.com.ng")

try:
    with urllib.request.urlopen(req, timeout=90) as r:
        print("Status:", r.status)
        print("CORS:", r.headers.get("Access-Control-Allow-Origin"))
        print("Body:", r.read()[:400])
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("CORS:", e.headers.get("Access-Control-Allow-Origin"))
    print("Body:", e.read()[:500])
except Exception as e:
    print("Error:", e)
