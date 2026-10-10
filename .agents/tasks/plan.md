# Implementation Plan — HTML → TSX Conversion + Backend Route Updates

> Workspace: `c:\Users\LENOVO\Downloads\mypy-tutor-main\mypy-tutor-main`
> Frontend build: `cd frontend && npm run build` (runs `tsc --noEmit && vite build`)
> Backend run: `uvicorn app.main:app --reload`
> Health check: `curl http://localhost:8000/health` → `{"status":"ok"}`

---

## Key findings from codebase exploration

- `frontend/src` currently has only 3 files: `main.tsx`, `api.ts`, `types.ts`. **`App.tsx` does not exist** but `main.tsx` already imports it — must be created.
- `frontend/src/styles/global.css` is imported by `main.tsx` — must also be created.
- React Router DOM v6.26 is installed. Token stored under multiple localStorage keys (`mpt_token`, `token`, `auth_token`, etc.) — the `useAuth` hook must try all of them.
- The backend already has `/payment`, `/terms`, `/privacy` routes that serve static HTML. They must be updated to 301-redirect to the SPA when `FRONTEND_URL` env var is set, with static HTML as fallback.
- The backend's `/verify/{cert_id}` route returns HTML (template substitution), not JSON. `CertificateVerifiedPage.tsx` needs a new JSON endpoint: `GET /api/verify/{cert_id}`.
- `paymentsApi.initialize()`, `paymentsApi.submitProof()`, `paymentsApi.bankDetails()` in `api.ts` must be used instead of hardcoded `'https://mypytutor.onrender.com'` in all pages.
- `API_BASE` is exported from `api.ts` — import it for any direct `fetch()` calls.
- All static HTML files must remain untouched (backend serves them as fallbacks and via the certificate email template system).

---

## FEAT-001 — Foundation: hooks, tokens, App.tsx, global CSS

- [ ] 1. Create `frontend/src/styles/global.css`.
      Already imported by `main.tsx` as `'./styles/global.css'` — if missing, the build fails.
      Content: body reset (margin/padding 0, box-sizing border-box, background `#07090f`,
      color `#e2e8f0`, font-family `'Segoe UI', Arial, sans-serif`, min-height 100vh).
      Files: `frontend/src/styles/global.css`
      Verify: `cd frontend && npm run build` — no "Cannot find module './styles/global.css'" error.

- [ ] 2. Create `frontend/src/styles/shared.ts` — design token constants.
      Export a `COLORS` const with all colour values from the HTML files:
      `bg: '#07090f'`, `cardBg: 'rgba(26,32,44,.95)'`, `textPrimary: '#e2e8f0'`,
      `textMuted: '#94a3b8'`, `textDisabled: '#64748b'`, `gold: '#f59e0b'`,
      `blue: '#3b82f6'`, `blueText: '#93c5fd'`, `green: '#48bb78'`, `red: '#ef4444'`,
      `codeText: '#fcd34d'`. Export a `RADIUS` const and a `Z` const for z-indices.
      Files: `frontend/src/styles/shared.ts`
      Verify: `cd frontend && npm run build` — no import errors.

- [ ] 3. Create `frontend/src/hooks/useAuth.ts`.
      Returns `{ token: string; learnerId: string; isSignedIn: boolean }`.
      Token resolution order (same as `payment.html` `_getToken()`):
      1. URL hash fragment `#token=...` or `#t=...` — if found, persist to localStorage `mpt_token` and strip the hash.
      2. URL query param `?token=...` — if found, persist to localStorage `mpt_token`.
      3. localStorage keys in order: `mpt_token`, `token`, `auth_token`, `access_token`, `jwt_token`, `user_token`, `mpt-token`.
      4. sessionStorage keys: `mpt_token`, `token`, `auth_token`.
      LearnerID resolution: localStorage `mpt_learner_id` → `learner_id`, then JWT decode
      (`JSON.parse(atob(tok.split('.')[1]))` → `payload.learner_id || payload.sub || payload.id`).
      Use `useState` + `useEffect` (listen for storage events) so it stays reactive.
      Files: `frontend/src/hooks/useAuth.ts`
      Verify: `cd frontend && npm run build` — no TypeScript errors.

- [ ] 4. Create `frontend/src/App.tsx`.
      Import `Routes`, `Route` from `react-router-dom`.
      Lazy-import all 6 page components with `React.lazy(() => import('./pages/...'))`.
      Wrap in `<React.Suspense fallback={<div style={{background:'#07090f',minHeight:'100vh'}}/>}>`.
      Add these routes:
      - `/payment` → `PaymentPage`
      - `/certificate/locked` → `CertificateLockedPage`
      - `/certificate/not-found` → `CertificateNotFoundPage`
      - `/verify/:certId` → `CertificateVerifiedPage`
      - `/terms` → `TermsPage`
      - `/privacy` → `PrivacyPage`
      - `*` → a minimal `<NotFoundPage>` (inline: `<div>404</div>`) so all imports resolve.
      Files: `frontend/src/App.tsx`
      Verify: `cd frontend && npm run build` — TypeScript checks pass (lazy imports resolve).

---

## FEAT-002 — Page components (6 TSX pages)

- [ ] 5. Create `frontend/src/pages/TermsPage.tsx`.
      Start with the simplest pages first.
      Render all 16 sections from `static/terms.html` as JSX.
      Use a single `<style>` JSX element (or inline-style objects) matching the CSS from `terms.html`
      (blue `#60a5fa` h2, `#fcd34d` h3, dark card boxes, footer links).
      Logo `<a>` → `https://mypytutor.com.ng`. Footer links `/terms` and `/privacy` use
      react-router `<Link>`. No API calls.
      Files: `frontend/src/pages/TermsPage.tsx`
      Verify: `cd frontend && npm run build` (zero errors). Then open `http://localhost:5173/terms`.

- [ ] 6. Create `frontend/src/pages/PrivacyPage.tsx`.
      Same pattern as TermsPage. Render all 9 sections from `static/privacy.html`.
      No API calls. Same dark-theme inline styles.
      Files: `frontend/src/pages/PrivacyPage.tsx`
      Verify: `cd frontend && npm run build`. Open `http://localhost:5173/privacy`.

- [ ] 7. Create `frontend/src/pages/certificates/CertificateNotFoundPage.tsx`.
      Read `certId` from `useParams<{ certId: string }>()`.
      Show the "Certificate Not Found" message with the cert ID in a `<code>` block,
      support email link (`tega.com.ng@gmail.com`), and a "Return to MyPy Tutor" button
      pointing to `https://mypytutor.com.ng`.
      Replicate the red theme, shake animation on the ❌ icon (use `@keyframes` inside a
      `<style>` JSX tag), slideUp animation, and the dark card with red top-border gradient.
      Files: `frontend/src/pages/certificates/CertificateNotFoundPage.tsx`
      Verify: `cd frontend && npm run build`.

- [ ] 8. Create `frontend/src/pages/certificates/CertificateVerifiedPage.tsx`.
      Get `certId` from `useParams<{ certId: string }>()`.
      On mount, `fetch(`${API_BASE}/api/verify/${certId}`)` (import `API_BASE` from `@/api`).
      If 404 response → `useNavigate()` to `/certificate/not-found?cert=${certId}`.
      If success, render the certificate card with: Recipient, Programme, Issued, Certificate ID, Status (Genuine).
      Replicate the confetti burst (CSS-only — 8 `.c` divs with `@keyframes confetti`),
      green theme, shimmer border, pulse badge, rowIn stagger animations — all via a
      `<style>` JSX element.
      Files: `frontend/src/pages/certificates/CertificateVerifiedPage.tsx`
      Verify: `cd frontend && npm run build`.

- [ ] 9. Create `frontend/src/pages/certificates/CertificateLockedPage.tsx`.
      Read plan params from `useSearchParams()`: `plan`, `amount`, `name` (plan display name),
      `tier` (level title like "Beginner").
      Import `useAuth` from `@/hooks/useAuth`. Import `paymentsApi`, `API_BASE` from `@/api`.
      Two tabs with `useState<'paystack'|'bank'>`:
      **Paystack tab**: button calls `paymentsApi.initialize()` with the token + learner ID.
      On success, `window.location.href = data.authorization_url`.
      If not signed in, show error: "Please sign in to MyPy Tutor first".
      **Bank Transfer tab**: `useEffect` loads bank details via `paymentsApi.bankDetails()`.
      Plan selector (same 4 plans as in the HTML), amount field, file upload (FileReader → base64 in state),
      notes textarea. Submit calls `paymentsApi.submitProof()`.
      Copy-to-clipboard for account number.
      Replicate all animations (float on lock icon, shimmer border, pulse on CTA button) via `<style>` JSX.
      Files: `frontend/src/pages/certificates/CertificateLockedPage.tsx`
      Verify: `cd frontend && npm run build`.

- [ ] 10. Create `frontend/src/pages/PaymentPage.tsx`.
       This is the most complex page — read `static/payment.html` in full before writing.
       Read params from `useSearchParams()`: `plan`, `name`, `amount`, `course`, `tier`, `coupon`, `desc`.
       Resolve plan details via the same `PLANS` mapping object as in `payment.html` (copy it as a TypeScript `Record<string, {name:string;amount:number;desc:string}>`).
       On mount: detect `?payment=success` → show success banner. Detect `#token=...` hash → persist to localStorage via `useAuth` logic (the hook handles this).
       **Paystack tab**: coupon code input + apply button (calls `POST ${API_BASE}/coupons/apply` with token); Pay button calls `paymentsApi.initialize()`. Show discounted price if coupon applied.
       **Bank Transfer tab**: loads bank details via `paymentsApi.bankDetails()` in `useEffect`. File upload (FileReader → base64). Submit via `paymentsApi.submitProof()`.
       20s timeout via `AbortController` for the Paystack init call (same as in `payment.html`).
       Replicate all UI: plan badge, plan title, plan amount header, options list, tab switch.
       All error/success alerts as inline-styled `<div>` with ok/err variants.
       Files: `frontend/src/pages/PaymentPage.tsx`
       Verify: `cd frontend && npm run build` — zero TS errors across all 10 source files.

---

## FEAT-003 — Backend route updates

- [ ] 11. Add `GET /api/verify/{cert_id}` JSON endpoint in `app/main.py`.
       Insert immediately after the existing `@app.get("/verify/{cert_id}")` route (around line 1776).
       Use the same DB query (select from `certificates` table by `cert_id`).
       Return `JSONResponse` with `{"cert_id", "learner_name", "level", "issued_at"}` on success.
       Return HTTP 404 `{"detail": "Certificate not found"}` if no record.
       No authentication required — same as the HTML route.
       Decorator: `@app.get("/api/verify/{cert_id}", include_in_schema=False)`.
       Files: `app/main.py`
       Verify: `curl -s http://localhost:8000/api/verify/NONEXISTENT` → `{"detail":"Certificate not found"}` with HTTP 404.

- [ ] 12. Update `GET /payment` to 301-redirect when `FRONTEND_URL` is set.
       In the existing `serve_payment_page` function (around line 7791), add `request: Request` parameter.
       At the top of the function body, check `_os.getenv("FRONTEND_URL", "")`:
       if set, return `RedirectResponse(url=f"{frontend_url}/payment?{str(request.url.query)}", status_code=301)`.
       Else, keep the existing static HTML serving code unchanged.
       Files: `app/main.py`
       Verify: `FRONTEND_URL=https://mypytutor.com.ng uvicorn app.main:app` then `curl -Ls http://localhost:8000/payment?plan=tier1` → HTTP 301 to `https://mypytutor.com.ng/payment?plan=tier1`.

- [ ] 13. Update `GET /terms` to 301-redirect when `FRONTEND_URL` is set.
       Same pattern as item 12. Add `request: Request` param to `serve_terms`.
       If `FRONTEND_URL` set → `RedirectResponse(url=f"{frontend_url}/terms", status_code=301)`.
       Else → existing static HTML serve (unchanged).
       Files: `app/main.py`
       Verify: With `FRONTEND_URL` set, `curl -Ls http://localhost:8000/terms` → 301 to `{FRONTEND_URL}/terms`.

- [ ] 14. Update `GET /privacy` to 301-redirect when `FRONTEND_URL` is set.
       Same pattern. Add `request: Request` to `serve_privacy`. Redirect to `{FRONTEND_URL}/privacy` or serve HTML fallback.
       Files: `app/main.py`
       Verify: With `FRONTEND_URL` set, `curl -Ls http://localhost:8000/privacy` → 301 to `{FRONTEND_URL}/privacy`.

- [ ] 15. Run full verification.
       Start backend, run frontend build, confirm all routes.
       Files: (no changes — verification step)
       Verify:
       ```
       cd frontend && npm run build
       # Then in another terminal:
       uvicorn app.main:app --reload
       curl -s http://localhost:8000/health
       curl -s http://localhost:8000/api/verify/NONEXISTENT
       pytest tests/
       ```
       Expected: build zero errors, health returns `{"status":"ok"}`, verify returns 404 JSON, all tests pass.

---

## Notes and decisions

1. **No App.tsx exists** — must create it from scratch. `main.tsx` already imports `./App`, so the build will fail until `App.tsx` exists.

2. **Cross-origin token fix** — the `useAuth` hook handles URL hash `#token=...` persistence into localStorage. This is the same pattern as `payment.html`'s `_getToken()` function. All pages that use `useAuth` automatically get this fix.

3. **`/api/verify/{cert_id}` JSON route** — the existing `/verify/{cert_id}` route only returns HTML. Rather than adding an `Accept: application/json` negotiation branch (which would change existing behaviour), a sibling `/api/verify/` route is cleanest.

4. **Backend redirect strategy** — adding 301 redirects guarded by `FRONTEND_URL` means: in dev (no `FRONTEND_URL`), the static HTML is served as before. In production (Render + Vercel, `FRONTEND_URL` set), the backend sends users to the React SPA. No breaking change.

5. **Static HTML files are NOT deleted** — they remain as fallbacks for: (a) routes that don't 301-redirect yet, (b) certificate email links that hit `/certificate/{level}` and `/verify/{cert_id}` directly on the backend.
