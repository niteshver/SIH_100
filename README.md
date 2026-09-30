# SIH26100 TenderHub — MVP

TenderHub is a demo-first procurement workspace for publishing tenders, receiving bidder applications and documents, and running evidence-grounded AI-assisted document checks. AI findings are advisory; procurement officers retain final decision authority.

## Local development

Frontend:

```bash
npm install
npm run dev
npm run typecheck
npm run build
```

Backend (Python 3.11):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" UPLOAD_DIR=./uploads uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8000
```

## Railway deployment checklist

Deploy the frontend and FastAPI backend as separate Railway services. The repository-root `Dockerfile` is for the frontend only.

**Backend service configuration (important for 502/503 errors):** set the backend service Root Directory to `/backend`. This makes Railway use `backend/Dockerfile` and `backend/railway.json` from this repository. The backend Dockerfile installs `app/requirements.txt` and starts `uvicorn app.main:app` on Railway's assigned `PORT`. Do not point the backend service at the repository-root frontend Dockerfile or the empty legacy file named `backend/Dockerfile 2`.

The API deliberately exits during startup if `SESSION_SECRET` is missing. If `/health` returns 502/503, inspect the backend service's **Deploy Logs** first: set `SESSION_SECRET` in the backend Variables if the log says it is missing, then redeploy. Generate a long random secret and keep it unchanged between deployments.

### Backend service variables

- `SESSION_SECRET`: required; a long, persistent random secret. Do not change it between deploys unless you intend to invalidate all sessions.
- `OFFICER_INVITE_CODE`: required only if officers are created through registration; keep it backend-only and share it only with authorized officers.
- `FRONTEND_ORIGINS=https://chatlyme.xyz,https://www.chatlyme.xyz`
- `UPLOAD_DIR=/data/uploads`
- `GEMINI_API_KEY`: set the key on the backend only. Never use a `VITE_*` name for secrets.
- `GEMINI_MODEL=gemini-2.5-flash`
- Optional Resend: `RESEND_API_KEY` and `RESEND_FROM_EMAIL` (must be a sender/domain verified with Resend).
- Optional Ollama fallback: `OLLAMA_BASE_URL` must be an HTTPS endpoint reachable by Railway and `OLLAMA_MODEL=llama3-groq-tool-use:8b`. Ollama running on your Mac at `localhost` is not reachable from Railway without a secure remote endpoint/tunnel. The API tries Gemini first and uses Ollama only when configured and reachable.

### Persistent uploads and records

Attach a Railway Volume to the backend service at mount path `/data`. Set `UPLOAD_DIR=/data/uploads`. The application stores uploaded files and its JSON record file under this directory. Without the mounted volume, local container files may be lost during redeploy/restart. For a larger or multi-replica production deployment, migrate JSON records to PostgreSQL and files to object storage.

### Frontend service variables

- `VITE_API_URL=https://api.chatlyme.xyz` after attaching that custom domain to the backend Railway service below.
- Because `VITE_API_URL` is a build-time variable, redeploy/rebuild the frontend after changing it.

### Required: same-site API domain for reliable login sessions

The frontend and API must use the same site for browser cookie sessions to work reliably when third-party cookies are blocked (especially in Incognito/private browsing). Do not leave the production API on the default `*.up.railway.app` domain while the UI runs on `chatlyme.xyz`.

1. In the **backend Railway service**, add the custom domain `api.chatlyme.xyz` and configure the DNS record using the exact target Railway displays.
2. Set backend variables:
   - `COOKIE_SECURE=true`
   - `COOKIE_SAMESITE=lax`
   - `FRONTEND_ORIGINS=https://chatlyme.xyz,https://www.chatlyme.xyz`
   - Keep `SESSION_SECRET` persistent across deploys.
3. In the **frontend Railway service**, set `VITE_API_URL=https://api.chatlyme.xyz`, then trigger a new frontend build/deploy. This variable is embedded at build time.
4. Verify in DevTools that the `register` or `login` response sets the `tenderhub_session` cookie for `api.chatlyme.xyz`, and that subsequent `/api/auth/me` and `/api/tenders` requests include that cookie and return 200.

The cookie is intentionally HttpOnly. Do not work around session failures by storing the session token in localStorage. The frontend also now builds bidder tender/application links under `/bidder/...` rather than incorrectly generating `/officer/...` links.

### Verify the deployment

1. Open `https://api.chatlyme.xyz/health` and confirm the JSON response contains `status: ok`. Separately confirm the Railway Volume is mounted at `/data`; the health endpoint does not prove that the volume is attached.
2. Register a bidder account and sign in. Register an officer account separately.
3. Publish a tender with at least one required document type and a future deadline.
4. Sign in as the bidder, open the tender, upload every required document, accept the terms, save the draft, and submit the bid.
5. Check that the application appears under My Applications and the officer's Bid Review, with document names and verification status.
6. If Gemini is unavailable and a remote Ollama endpoint is configured, verification should fall back; if both fail or a file has no extractable text, the result must remain flagged for manual review.
7. Email notifications are optional. Configure Resend's API key and verified sender to send submission and verification updates.

## Safety notes

Text extraction and RAG can identify missing evidence and inconsistencies; they cannot prove that a document is legally authentic. Keep human review mandatory. Store API keys only in backend Railway Variables. Do not use a local Mac Ollama URL as a Railway service URL.
