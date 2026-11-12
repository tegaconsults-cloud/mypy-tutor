"""
MyPyTutor 2.0 Launch Email Trigger
===================================
Run this script to send the launch announcement to ALL users.

Usage:
    python scripts/trigger_launch_email.py --admin-email YOUR_ADMIN_EMAIL --admin-password YOUR_ADMIN_PASSWORD

The script will:
1. Sign in as admin
2. Fire the /admin/announce endpoint with the MyPyTutor 2.0 launch email
3. The backend auto-sends it to every confirmed user
"""

import urllib.request
import urllib.error
import json
import argparse
import sys

BASE = "https://mypytutor.onrender.com"

LAUNCH_SUBJECT = "MyPyTutor 2.0 is here — your AI-powered Python learning just got better 🚀"

LAUNCH_MESSAGE = """Hi there,

We have been working hard behind the scenes, and today we are proud to announce MyPyTutor 2.0 — the most significant upgrade to your learning experience since we launched.

Here is everything that is new for you:

🤖 SIR TEGA AI TUTOR — UPGRADED
Sir Tega now explains every topic in clear, written language before offering code examples. He suggests related topics after every lesson so you always know what to learn next. His knowledge now spans the full Python, AI and Machine Learning curriculum.

📚 23 COURSES ACROSS THREE PILLARS
MyPyTutor 2.0 brings a full structured curriculum covering:
• Python Programming and Software Development
• Artificial Intelligence and Generative AI — including prompt engineering, AI agents, RAG and LLM development
• Machine Learning and Data Science — including deep learning, NLP, computer vision, reinforcement learning and MLOps

💳 FLEXIBLE LEARNING PLANS
You can now choose how you learn:
• Free Plan — selected introductory lessons and limited AI access
• Pro Plan — ₦4,500/month — full Python and AI course catalogue, 300 AI tutor sessions/month
• Premium Plan — ₦8,500/month — everything including advanced ML courses, 800 AI tutor sessions/month
• Individual courses — from ₦7,500 — buy just the course you need, with lifetime access
• Course bundles — from ₦17,500 — save more by learning a full pathway together

Annual plans are also available (save approximately two months compared to paying monthly).

⚡ PERFORMANCE IMPROVEMENTS
The platform is significantly faster. Cold-start times have been reduced, the course catalogue loads from cache, and AI responses are more reliable with smarter fallback between providers.

🎓 CERTIFICATES
Earn verifiable certificates from Teamsamikoko Global Academy (Reg No: 3508656) on eligible course completions.

👥 REFERRAL REWARDS
Share your referral link and earn 15% of every qualifying first purchase made by learners you refer.

HOW TO EXPLORE THE NEW FEATURES
1. Sign in at https://www.mypytutor.com.ng
2. Visit the Pricing page to see all available plans and courses
3. Ask Sir Tega about any Python, AI or Machine Learning topic — notice how he now explains concepts in depth before offering code
4. Check your profile for your current plan and AI usage

We would love to hear your thoughts. If you have feedback, questions or suggestions, reach us through the Support/Enquiry form on the platform.

Thank you for being part of MyPyTutor. This is just the beginning.

With warm regards,
Sir. Tega
AI Tutor and Founder
MyPyTutor — mypytutor.com.ng
Built by TeamTega Technologies Limited | Backed by Teamsamikoko Global Academy"""


def req(method, path, body=None, token=None, timeout=60):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


ADMIN_EMAIL = "tegaconsults@gmail.com"


def main():
    parser = argparse.ArgumentParser(description="Trigger MyPyTutor 2.0 launch email")
    parser.add_argument("--admin-password", required=False, help="Admin password")
    parser.add_argument("--token", required=False, help="Admin token (skip login)")
    args = parser.parse_args()

    if not args.admin_password and not args.token:
        print("❌ Provide either --admin-password or --token")
        sys.exit(1)

    if args.token:
        token = args.token
        print("✅ Using provided token.")
    else:
        print(f"Step 1 — Signing in as {ADMIN_EMAIL}...")
        status, data = req("POST", "/admin/login", {
            "email": ADMIN_EMAIL,
            "password": args.admin_password,
        })
        if status != 200 or "token" not in data:
            print(f"❌ Admin login failed ({status}): {data}")
            sys.exit(1)
        token = data["token"]
        print(f"✅ Signed in. Token acquired.")

    print("\nStep 2 — Sending MyPyTutor 2.0 launch email to all users...")
    status, data = req("POST", "/admin/announce", {
        "target": "all",
        "subject": LAUNCH_SUBJECT,
        "message": LAUNCH_MESSAGE,
    }, token=token)

    if status == 200 and data.get("ok"):
        sent = data.get("sent_to", "?")
        print(f"✅ Launch email sent to {sent} users!")
        print(f"   Message: {data.get('message', '')}")
    else:
        print(f"❌ Announcement failed ({status}): {data}")
        sys.exit(1)


if __name__ == "__main__":
    main()
