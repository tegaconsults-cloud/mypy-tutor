# MyPy Tutor — Frontend

Static frontend for MyPy Tutor, ready to deploy on **Vercel**.

The FastAPI backend stays on **Render** (unchanged). This folder contains
only the HTML, CSS, JS, and assets the browser needs.

---

## Deploy to Vercel

### One-click (recommended)

1. Push this `frontend/` folder to a GitHub repo (or a subfolder of one).
2. Go to [vercel.com/new](https://vercel.com/new) → Import that repo.
3. Set **Root Directory** to `frontend` if it's a subfolder.
4. No build command needed — this is a static site.
5. Add one environment variable in the Vercel dashboard:

| Variable       | Value                                  |
|----------------|----------------------------------------|
| `VITE_API_URL` | `https://mypytutor.onrender.com`       |

> The `API_BASE` constant in `index.html` and `admin.html` is currently
> hardcoded to `https://mypytutor.onrender.com`. If you change your
> backend URL, update both files' `API_BASE` constant, or wire it up
> to a build step.

---

## Backend CORS

After deploying, add your Vercel URL to the backend's allowed origins.

In `render.yaml` (or the Render dashboard), set:

```
RENDER_EXTERNAL_URL=https://your-frontend.vercel.app
```

Or add it explicitly in `app/main.py` → `_allowed_origins`.

---

## Google OAuth redirect URI

In the Google Cloud Console, add your Vercel URL as an authorised redirect URI:

```
https://your-frontend.vercel.app/auth/google/callback
```

The backend's `APP_URL` env var must also be updated to your Vercel URL
so the redirect after Google login points to the right place:

```
APP_URL=https://your-frontend.vercel.app
```

Set this in the Render dashboard for the backend service.

---

## Local development

Serve the folder with any static server:

```bash
npx serve .
# or
python -m http.server 3000
```

The `API_BASE` in `index.html` points directly to the Render backend, so
local dev works without any proxy as long as the backend is running.

---

## File structure

```
frontend/
├── index.html       # Main app (single page)
├── admin.html       # Admin panel
├── premium.css      # Design system
├── sw.js            # Service worker (PWA)
├── manifest.json    # PWA manifest
├── favicon.ico
├── icons/           # App icons
├── vercel.json      # Vercel config (headers + /api/* rewrite)
└── .env.example     # Environment variable reference
```
