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

**Deploy the frontend and backend as two separate Railway services.** The root `Dockerfile` is the Vite frontend. The dedicated FastAPI Dockerfile is `backend/Dockerfile`.

### 1. Configure the FastAPI backend service

In Railway, create or select the backend service for this repository and set:

- **Root Directory:** `/backend`
- **Builder:** Dockerfile (Railway reads `backend/Dockerfile` relative to the configured root directory).
- **Healthcheck path:** `/health` (also configured in `backend/railway.json`).
- **Volume:** attach a Railway Volume mounted at `/data`.

Set these backend service variables in Railway:

- `SESSION_SECRET`: a long, persistent random secret. The backend intentionally fails to start if this is missing. Generate one locally with `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Do not commit or share it, and do not change it between deploys unless you intend to invalidate all sessions.
- `UPLOAD_DIR=/data/uploads`
- `FRONTEND_ORIGINS=https://chatlyme.xyz,https://www.chatlyme.xyz`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=lax`
- `GEMINI_API_KEY`: set this on the backend only if you want Gemini document analysis.
- `GEMINI_MODEL=gemini-2.5-flash`
- Optional Resend: `RESEND_API_KEY` and `RESEND_FROM_EMAIL` (must be a sender/domain verified with Resend).
- Optional Ollama fallback: `OLLAMA_BASE_URL` must be an HTTPS endpoint reachable by Railway and `OLLAMA_MODEL=llama3-groq-tool-use:8b`. Ollama running on your Mac at `localhost` is not reachable from Railway without a secure remote endpoint/tunnel.

The backend container installs `backend/requirements.txt`, copies the `backend/app` package, binds to `0.0.0.0:$PORT`, and starts `uvicorn app.main:app`. Do not run the root Vite `npm start` command as the backend start command.

### 2. Configure the frontend service

Keep the frontend service's root directory at the repository root so it uses the root `Dockerfile`. Set:

- `VITE_API_URL=https://api.chatlyme.xyz`

Attach the custom domain `api.chatlyme.xyz` to the **backend service**, using the exact DNS target Railway displays. In the frontend service, trigger a fresh build/deploy after changing `VITE_API_URL`; Vite embeds this variable during the build.

The frontend and API must use the same site for browser cookie sessions to work reliably when third-party cookies are blocked (especially in Incognito/private browsing). Do not leave the production API on the default `*.up.railway.app` domain while the UI runs on `chatlyme.xyz`.

### 3. Verify the deployment in order

1. Open `https://api.chatlyme.xyz/health`. It should return JSON with `"status":"ok"`. The response also reports whether the upload path is configured under `/data` and whether Gemini/Ollama variables are configured; this does not prove that a Railway Volume is attached, so verify the Volume in Railway as well.
2. If health returns 502/503, open the **backend service's latest deployment logs**. Check for `SESSION_SECRET must be configured`, dependency installation failures, or an import/startup traceback. Do not debug the React login form until the backend starts successfully.
3. Register a bidder and sign in. Verify the `register` or `login` response sets the HttpOnly `tenderhub_session` cookie for `api.chatlyme.xyz`.
4. Verify `/api/auth/me`, `/api/tenders`, and `/api/bids` return 200 with the session cookie.
5. Publish a tender with a future deadline and required document types. Sign in as the bidder, open the tender, upload the required documents, save the draft, and submit the bid. Check My Applications and the officer's Bid Review for document names and verification status.

### 4. Persistence and production scope

The app stores uploaded files and JSON records under `UPLOAD_DIR`. Without a mounted volume, files and records can be lost on restart/redeploy. A local JSON file is suitable only for a single-replica MVP; for multi-replica or higher-volume production use PostgreSQL for records and object storage for documents.

## Safety notes

Text extraction and RAG can identify missing evidence and inconsistencies; they cannot prove that a document is legally authentic. Keep human review mandatory. Store API keys only in backend Railway Variables. Do not use a local Mac Ollama URL as a Railway service URL.
