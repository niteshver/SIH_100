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

Deploy the frontend and FastAPI backend as separate services.

### Backend service variables

- `SESSION_SECRET`: a long, persistent random secret. Do not change it between deploys unless you intend to invalidate all sessions.
- `FRONTEND_ORIGINS=https://chatlyme.xyz,https://www.chatlyme.xyz`
- `UPLOAD_DIR=/data/uploads`
- `GEMINI_API_KEY`: set the key on the backend only. Never use a `VITE_*` name for secrets.
- `GEMINI_MODEL=gemini-2.5-flash`
- Optional Resend: `RESEND_API_KEY` and `RESEND_FROM_EMAIL` (must be a sender/domain verified with Resend).
- Optional Ollama fallback: `OLLAMA_BASE_URL` must be an HTTPS endpoint reachable by Railway and `OLLAMA_MODEL=llama3-groq-tool-use:8b`. Ollama running on your Mac at `localhost` is not reachable from Railway without a secure remote endpoint/tunnel. The API tries Gemini first and uses Ollama only when configured and reachable.

### Persistent uploads and records

Attach a Railway Volume to the backend service at mount path `/data`. Set `UPLOAD_DIR=/data/uploads`. The application stores uploaded files and its JSON record file under this directory. Without the mounted volume, local container files may be lost during redeploy/restart. For a larger or multi-replica production deployment, migrate JSON records to PostgreSQL and files to object storage.

### Frontend service variables

- `VITE_API_URL=https://sih100-production.up.railway.app` (use the active public domain shown in the backend service's Networking settings).
- Because `VITE_API_URL` is a build-time variable, redeploy/rebuild the frontend after changing it.

### Verify the deployment

1. Open `https://sih100-production.up.railway.app/health`. Check `status: ok`, AI configuration flags, and `storage: volume_path_configured`.
2. Register a bidder account and sign in. Register an officer account separately.
3. Publish a tender with at least one required document type and a future deadline.
4. Sign in as the bidder, open the tender, upload every required document, accept the terms, save the draft, and submit the bid.
5. Check that the application appears under My Applications and the officer's Bid Review, with document names and verification status.
6. If Gemini is unavailable and a remote Ollama endpoint is configured, verification should fall back; if both fail or a file has no extractable text, the result must remain flagged for manual review.
7. Email notifications are optional. Configure Resend's API key and verified sender to send submission and verification updates.

## Safety notes

Text extraction and RAG can identify missing evidence and inconsistencies; they cannot prove that a document is legally authentic. Keep human review mandatory. Store API keys only in backend Railway Variables. Do not use a local Mac Ollama URL as a Railway service URL.
