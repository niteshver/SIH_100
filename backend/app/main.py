from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timezone

app = FastAPI(title="SIH26100 Bid Compliance API", version="0.1.0")
UPLOADS = Path("uploads")
UPLOADS.mkdir(exist_ok=True)

class Decision(BaseModel):
    bidder_id: str
    decision: str
    note: str = ""

@app.get("/health")
def health():
    return {"status": "ok", "mode": "demo", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/tenders")
def tenders():
    return [{"id": "GEM/2026/B/4819201", "title": "Mechanical Seals & Spares", "status": "evaluation", "bidder_count": 12, "closing_date": "2026-09-24"}]

@app.get("/api/tenders/{tender_id}/report")
def report(tender_id: str):
    return {"tender_id": tender_id, "mode": "demo", "human_review_required": True, "ai_can_decide": False, "summary": "Evidence-backed compliance signals are ready for officer review.", "risks": [{"type": "document_gap", "severity": "medium", "message": "2 bidder documents need clarification."}]}

@app.post("/api/documents/upload")
async def upload(file: UploadFile = File(...)):
    allowed = {"application/pdf", "image/png", "image/jpeg"}
    if file.content_type not in allowed:
        raise HTTPException(415, "Only PDF, PNG, and JPEG files are accepted")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 10 MB limit")
    safe_name = Path(file.filename or "document").name
    destination = UPLOADS / safe_name
    destination.write_bytes(data)
    return {"status": "uploaded", "filename": safe_name, "pipeline": ["uploaded", "extracting", "validating", "matching", "human_review"], "verification_source": "Demo Verification Source"}

@app.post("/api/decisions")
def decision(payload: Decision):
    if payload.decision not in {"Reviewed", "Needs clarification"}:
        raise HTTPException(400, "Officer decision is required; AI cannot qualify or disqualify bidders")
    return {"status": "recorded", "audit_event": {**payload.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()}}
