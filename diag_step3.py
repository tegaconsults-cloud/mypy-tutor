import urllib.request, json, ssl, time
ctx = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"

def hit(method, path, body=None, token=None):
    url = BASE + path
    headers = {"Content-Type":"application/json","User-Agent":"DiagBot/1.0"}
    if token: headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            try: return r.status, json.loads(r.read().decode())
            except: return r.status, r.read().decode()[:100]
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except: return e.code, e.read().decode()[:100]
    except Exception as e: return 0, str(e)[:80]

ts = int(time.time())
email = f"step3test{ts}@test.com"
print(f"Testing with: {email}")
print()

# Signup
time.sleep(5)
s,d = hit("POST", "/auth/signup", {"email": email, "name": "Step3 Test", "password": "Test1234!"})
icon = "✅" if 200<=s<300 else "❌"
print(f"{icon} [{s}] signup: {d}")

# Signin (will fail until confirmed — expected)
time.sleep(5)
s,d = hit("POST", "/auth/signin", {"email": email, "password": "Test1234!"})
icon = "✅" if 200<=s<300 else "⚠️"
print(f"{icon} [{s}] signin (pre-confirm): {d}")

# Auth config
time.sleep(5)
s,d = hit("GET", "/auth/config")
enabled = d.get("google_enabled", False) if isinstance(d,dict) else False
google_id = d.get("google_client_id","") if isinstance(d,dict) else ""
icon = "✅" if 200<=s<300 else "❌"
print(f"{icon} [{s}] auth_config: google_enabled={enabled}, client_id_set={bool(google_id)}")

# Payment webhook test - validate endpoint exists
time.sleep(5)
s,d = hit("GET", "/payments/bank-details")
icon = "✅" if 200<=s<300 else "❌"
bank = d.get("bank_name","") if isinstance(d,dict) else ""
acct = d.get("account_number","") if isinstance(d,dict) else ""
print(f"{icon} [{s}] bank_details: {bank} | acct_set={bool(acct)}")

# Paystack - check webhook endpoint exists (should 400 on GET, not 404)
time.sleep(5)
s,d = hit("GET", "/webhooks/paystack")
print(f"[{s}] paystack_webhook_endpoint: {'EXISTS' if s != 404 else 'MISSING'} ({d})")

# Referral - create code for new user
time.sleep(5)
s,d = hit("GET", "/referral/default")
icon = "✅" if 200<=s<300 else "⚠️"
print(f"{icon} [{s}] referral: {str(d)[:80]}")

# Courses - check ai-automation exists in catalog
time.sleep(5)
s,d = hit("GET", "/courses/catalog")
if isinstance(d, dict) and "courses" in d:
    names = [c["name"] for c in d["courses"]]
    ai_auto = "ai-automation" in names
    print(f"✅ [{s}] courses_catalog: {len(names)} courses | ai-automation={ai_auto}")
else:
    print(f"❌ [{s}] courses_catalog: {str(d)[:60]}")

print()
print("Step 3 complete.")
