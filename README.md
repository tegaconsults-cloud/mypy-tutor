# MyPy Tutor

MyPy Tutor is an AI-powered Python learning platform that combines a conversational tutor, structured courses, quizzes, progress tracking, and certification-oriented features.

## What the product does

- AI tutor chat for Python questions and coding help
- Guided learning paths for beginners, course-based study, interview prep, and quizzes
- Learner progress tracking with XP, badges, and knowledge-gap insights
- Authentication, profiles, and premium features such as referrals, coupons, and access codes
- Certificate generation and feedback/survey flows

## Tech stack

### Backend
- Python
- FastAPI
- Pydantic
- SQLite for local persistence
- Supabase integration for cloud-backed features

### Frontend
- React + TypeScript
- Vite
- Tailwind CSS
- Framer Motion

## Project layout

- app/ — FastAPI backend, auth, LLM integration, course logic, and database access
- frontend-react/ — active React/Vite frontend used for the main experience
- frontend/ — legacy/static frontend assets
- static/ — static site files and assets
- docs/ — SQL and migration notes
- tests/ — backend test coverage

## Local development

### 1) Create and activate a virtual environment

Windows powershell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt -r requirements-dev.txt
```

### 3) Configure environment variables

Copy [.env.example](.env.example) to .env and fill in the required values, especially:

- GROQ_API_KEY
- SESSION_SECRET
- GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
- EMAIL_* values if email auth is enabled

### 4) Run the backend

```powershell
uvicorn app.main:app --reload
```

### 5) Run the frontend

```powershell
cd frontend-react
npm install
npm run dev
```

## Frontend strategy

The canonical frontend for active development is [frontend-react](frontend-react). The other frontend folders are retained as legacy or alternative assets and should not be treated as the main target for new work.

## Deployment notes

The backend is designed to work with Render-style deployments and supports environment-based configuration. For production, ensure the required secret values are set in the deployment environment.

## Quality checks

Run backend tests:

```powershell
pytest -q
```

Run the frontend build:

```powershell
cd frontend-react
npm run build
```
