# MyPy Tutor — Backend

AI-powered Python learning platform. FastAPI backend deployed on Render.

**Frontend repo:** [tegaconsults-cloud/mypytutor](https://github.com/tegaconsults-cloud/mypytutor) (React/Vite — deployed on Vercel at [mypytutor.com.ng](https://mypytutor.com.ng))

## What the product does

- AI tutor chat for Python questions and coding help (Groq LLM — Llama 3.3 70B)
- 16 structured courses from Python Fundamentals to Machine Learning
- Quizzes, assignments, XP, badges, and knowledge-gap tracking
- Email + Google + GitHub auth, referral programme, Paystack payments
- Certificate generation (Basic / Advanced / Executive Masters)

## Repo layout

```
app/          FastAPI routes, auth, LLM, courses, DB, email
static/       Admin dashboard HTML, icons, robots.txt, sitemap, SW
docs/         Supabase SQL schemas and migration scripts
tests/        Pytest test suite
requirements.txt      Production dependencies
requirements-dev.txt  Dev/test dependencies
render.yaml           Render deployment config
```

## Tech stack

- **Python 3.11** / FastAPI / Uvicorn
- **SQLite** (local, WAL mode) + **Supabase** (cloud dual-write)
- **Groq API** — Llama 3.3 70B (smart) / Llama 3.1 8B (fast)
- **Resend** (primary) + Gmail SMTP (fallback) for email

## Local development

### 1. Virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Environment variables

```powershell
Copy-Item .env.example .env
# Edit .env — set GROQ_API_KEY, SESSION_SECRET, GOOGLE_CLIENT_ID, etc.
```

### 3. Run the backend

```powershell
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. See `/health` to confirm.

### 4. Run the frontend (separate repo)

```powershell
cd ..\mypytutor-frontend   # or clone tegaconsults-cloud/mypytutor
npm install
npm run dev
```

## Tests

```powershell
pytest -q
```

## Deployment

Backend → Render (config in `render.yaml`)
Frontend → Vercel (auto-deploys from `tegaconsults-cloud/mypytutor`)
