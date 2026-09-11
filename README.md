# SIH26100 Bid Compliance Platform

A demo-first, evidence-backed procurement review workspace for CPCL. The frontend is a Vite + React + TypeScript dashboard; the optional backend is a FastAPI service with seeded demo endpoints, safe uploads, verification pipeline states, and human decision audit controls.

## Run frontend

```bash
npm install
npm run dev
```

## Run backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The default mode is intentionally deterministic and labeled as demo verification. AI output is advisory and never qualifies or disqualifies a bidder; procurement officers record the final decision.
