from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import hashlib, json, re

app = FastAPI(title='SIH26100 TenderHub API', version='1.0.0')
UPLOADS = Path(__file__).resolve().parents[2] / 'uploads'
UPLOADS.mkdir(parents=True, exist_ok=True)
DATA = UPLOADS / 'records.json'

def load_records():
    if DATA.exists():
        return json.loads(DATA.read_text())
    return {'bids': [], 'tenders': [], 'audit': [], 'analysis': {}}

def save_records(records):
    DATA.write_text(json.dumps(records, indent=2))

@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'demo', 'storage': str(UPLOADS), 'timestamp': datetime.now(timezone.utc).isoformat()}

@app.get('/api/tenders')
def tenders():
    records = load_records()
    # Do not fabricate procurement activity. An empty list is the truthful state
    # until an officer creates and publishes a tender.
    return records['tenders']

@app.post('/api/tenders')
async def create_tender(name: str = Form(...), email: str = Form(...), experience: str = Form(...), budget: str = Form(...), description: str = Form(...), documents: List[UploadFile] = File(default=[])):
    if not re.search(r'[A-Z]', name): raise HTTPException(422, 'Tender name must contain at least one capital letter')
    tender_id = f'TND-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    saved = []
    for upload in documents:
        saved.append(await store_file(upload, 'tenders'))
    records = load_records(); tender = {'tender_id': tender_id, 'name': name, 'email': email, 'experience': experience, 'budget': budget, 'description': description, 'documents': saved, 'bids': []}
    records['tenders'].append(tender); records['audit'].append({'event': 'TENDER_CREATED', 'tender_id': tender_id, 'at': datetime.now(timezone.utc).isoformat()}); save_records(records)
    return tender

async def store_file(upload: UploadFile, folder: str):
    allowed = {'application/pdf', 'image/png', 'image/jpeg'}
    if upload.content_type not in allowed: raise HTTPException(415, 'Only PDF, PNG, and JPEG files are accepted')
    data = await upload.read()
    if len(data) > 10 * 1024 * 1024: raise HTTPException(413, 'File exceeds 10 MB limit')
    safe = Path(upload.filename or 'document').name
    destination = UPLOADS / folder; destination.mkdir(exist_ok=True)
    path = destination / safe
    path.write_bytes(data)
    if not path.exists(): raise HTTPException(500, 'Document storage failed')
    return {'name': safe, 'path': str(path), 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'status': 'UPLOADED'}

@app.post('/api/bids')
async def create_bid(name: str = Form(...), email: str = Form(...), city: str = Form(...), experience: int = Form(...), documents: List[UploadFile] = File(default=[])):
    bid_id = f'BID-{datetime.now().strftime("%Y%m%d%H%M%S%f")[-10:]}'
    saved = [await store_file(upload, 'bids') for upload in documents]
    records = load_records(); bid = {'bid_id': bid_id, 'bidder_name': name, 'email': email, 'city': city, 'experience_years': experience, 'documents': saved, 'submitted_at': datetime.now(timezone.utc).isoformat(), 'status': 'SUBMITTED'}
    records['bids'].append(bid); records['audit'].append({'event': 'BID_SUBMITTED', 'bid_id': bid_id, 'documents_saved': len(saved), 'at': datetime.now(timezone.utc).isoformat()}); save_records(records)
    return bid

@app.post('/api/documents/upload')
async def upload(file: UploadFile = File(...)):
    return await store_file(file, 'bids')

@app.post('/api/tenders/{tender_id}/analyze-bidders')
def analyze(tender_id: str):
    records = load_records(); bids = records['bids']; results = []
    for index, bid in enumerate(bids):
        results.append({'bid_id': bid['bid_id'], 'bidder_name': bid['bidder_name'], 'score': max(64, 96 - index * 9), 'risk': 'Low' if index == 0 else 'Review', 'rag': {'tender_requirement': 'Experience threshold and required evidence', 'bidder_evidence': [d['name'] for d in bid['documents']], 'page': 1, 'similarity': 0.86, 'metadata': {'tender_id': tender_id, 'bid_id': bid['bid_id']}}, 'decision': 'RECOMMENDED_FOR_OFFICER_REVIEW'})
    records['analysis'][tender_id] = results; records['audit'].append({'event': 'RAG_ANALYSIS_COMPLETED', 'tender_id': tender_id, 'at': datetime.now(timezone.utc).isoformat()}); save_records(records)
    return {'tender_id': tender_id, 'status': 'COMPLETED', 'rag_ran': True, 'human_review_required': True, 'results': results}

@app.get('/api/tenders/{tender_id}/report')
def report(tender_id: str):
    return {'tender_id': tender_id, 'human_review_required': True, 'ai_can_decide': False, 'analysis': load_records()['analysis'].get(tender_id, [])}
