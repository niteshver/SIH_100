from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import hashlib, json, re, shutil, tempfile, zipfile

app = FastAPI(title='SIH26100 TenderHub API', version='2.0.0')
UPLOADS = Path(__file__).resolve().parent / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
DATA = UPLOADS / 'records.json'
MAX_FILE = 10 * 1024 * 1024
ALLOWED = {'pdf', 'png', 'jpg', 'jpeg'}

def now(): return datetime.now(timezone.utc).isoformat()
def load_records():
    if DATA.exists():
        data = json.loads(DATA.read_text())
        data.setdefault('bids', []); data.setdefault('tenders', []); data.setdefault('audit', []); data.setdefault('analysis', {})
        return data
    return {'bids': [], 'tenders': [], 'audit': [], 'analysis': {}}
def save_records(records): DATA.write_text(json.dumps(records, indent=2))
def audit(event, **meta):
    records = load_records(); records['audit'].append({'event': event, 'at': now(), **meta}); save_records(records)
def safe_name(filename):
    name = Path(filename or 'document').name.replace('..', '_')
    if name.startswith('.') or not name: raise HTTPException(400, 'Hidden or empty filenames are not allowed')
    return name
def extension(name): return Path(name).suffix.lower().lstrip('.')

@app.get('/health')
def health(): return {'status':'ok','mode':'demo-fallback','storage':'local demo storage; configure PostgreSQL/S3 for production','timestamp':now()}
@app.get('/api/tenders')
def tenders(): return load_records()['tenders']
@app.get('/api/bids')
def bids(): return load_records()['bids']
@app.get('/api/audit')
def get_audit(): return load_records()['audit']

async def store_file(upload: UploadFile, folder: str):
    name = safe_name(upload.filename); ext = extension(name)
    if ext == 'zip': return await store_zip(upload, folder)
    if ext not in ALLOWED: raise HTTPException(415, 'Accepted formats: PDF, PNG, JPG, JPEG and ZIP')
    data = await upload.read()
    if len(data) > MAX_FILE: raise HTTPException(413, 'File exceeds 10 MB limit')
    destination = UPLOADS / folder; destination.mkdir(exist_ok=True)
    unique = f'{hashlib.sha256(data).hexdigest()[:12]}-{name}'
    path = destination / unique; path.write_bytes(data)
    return {'name':name,'stored_name':unique,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'status':'UPLOADED','classification':'REQUIRES_MANUAL_REVIEW','extraction':'PENDING'}

async def store_zip(upload: UploadFile, folder: str):
    data = await upload.read()
    if len(data) > 25 * 1024 * 1024: raise HTTPException(413, 'ZIP exceeds 25 MB limit')
    if not zipfile.is_zipfile(tempfile.SpooledTemporaryFile()):
        pass
    temp = Path(tempfile.mkdtemp(prefix='tenderhub-'))
    try:
        archive = temp / 'upload.zip'; archive.write_bytes(data)
        with zipfile.ZipFile(archive) as z:
            members = [m for m in z.infolist() if not m.is_dir() and '__MACOSX' not in m.filename and not Path(m.filename).name.startswith('.')]
            if len(members) > 50: raise HTTPException(413, 'ZIP contains too many files')
            total = sum(m.file_size for m in members)
            if total > 50 * 1024 * 1024: raise HTTPException(413, 'Extracted ZIP content exceeds 50 MB')
            output=[]; destination=UPLOADS/folder; destination.mkdir(exist_ok=True)
            for member in members:
                name=safe_name(member.filename); ext=extension(name)
                if ext not in ALLOWED: raise HTTPException(415, f'Unsupported ZIP file: {name}')
                content=z.read(member); digest=hashlib.sha256(content).hexdigest(); stored=f'{digest[:12]}-{name}'
                (destination/stored).write_bytes(content); output.append({'name':name,'stored_name':stored,'size':len(content),'sha256':digest,'status':'UPLOADED','classification':'REQUIRES_MANUAL_REVIEW','extraction':'PENDING'})
            return {'name':upload.filename or 'documents.zip','status':'EXTRACTED','files':output,'count':len(output)}
    except zipfile.BadZipFile: raise HTTPException(400, 'Invalid ZIP archive')
    finally: shutil.rmtree(temp, ignore_errors=True)

@app.post('/api/tenders')
async def create_tender(name: str=Form(...), email: str=Form('demo@tenderhub.local'), experience: str=Form(...), budget: str=Form(...), description: str=Form(...), department: str=Form('Procurement'), deadline: str=Form(...), turnover: str=Form(''), documents: List[UploadFile]=File(default=[])):
    if len(name.strip()) < 4: raise HTTPException(422, 'Tender title is required')
    saved=[]
    for upload in documents: saved.append(await store_file(upload,'tenders'))
    tender={'tender_id':f'TND-{datetime.now().strftime("%Y%m%d%H%M%S")}', 'name':name, 'email':email, 'experience':experience, 'turnover':turnover, 'budget':budget, 'description':description, 'department':department, 'deadline':deadline, 'documents':saved, 'requirements':['Minimum experience: '+experience, 'Required turnover: '+turnover if turnover else 'Turnover review required'], 'status':'OPEN', 'bids':0, 'created_at':now()}
    records=load_records(); records['tenders'].append(tender); records['audit'].append({'event':'TENDER_PUBLISHED','tender_id':tender['tender_id'],'at':now(),'documents':len(saved)}); save_records(records); return tender

@app.post('/api/bids')
async def create_bid(tender_id: str=Form(...), name: str=Form(...), email: str=Form(...), city: str=Form(...), experience: int=Form(...), bid_amount: str=Form(''), pan: str=Form(''), gstin: str=Form(''), declaration: str=Form(...), documents: List[UploadFile]=File(default=[])):
    records=load_records(); tender=next((t for t in records['tenders'] if t['tender_id']==tender_id),None)
    if not tender: raise HTTPException(404,'Tender not found')
    if tender.get('deadline') and datetime.fromisoformat(tender['deadline']).replace(tzinfo=timezone.utc) < datetime.now(timezone.utc): raise HTTPException(409,'Tender deadline has expired')
    if not declaration.strip(): raise HTTPException(422,'Declaration is required')
    if any(b.get('tender_id')==tender_id and b.get('email')==email for b in records['bids']): raise HTTPException(409,'Duplicate bid is not allowed')
    saved=[item for upload in documents for item in [await store_file(upload,'bids')]]
    bid={'bid_id':f'BID-{datetime.now().strftime("%Y%m%d%H%M%S%f")[-12:]}','tender_id':tender_id,'bidder_name':name,'email':email,'city':city,'experience_years':experience,'bid_amount':bid_amount,'pan':pan,'gstin':gstin,'documents':saved,'submitted_at':now(),'status':'LOCKED','verification_status':'API_UNAVAILABLE','analysis_source':'Rule-Based Fallback','score':None,'risk':'REQUIRES_REVIEW'}
    records['bids'].append(bid)
    for item in records['tenders']:
        if item['tender_id']==tender_id: item['bids']=sum(1 for b in records['bids'] if b.get('tender_id')==tender_id)
    records['audit'].append({'event':'BID_SUBMITTED','bid_id':bid['bid_id'],'tender_id':tender_id,'at':now(),'human_review_required':True}); save_records(records); return bid

@app.post('/api/documents/upload')
async def upload(file: UploadFile=File(...)): return await store_file(file,'bids')
@app.post('/api/tenders/{tender_id}/analyze-bidders')
def analyze(tender_id: str):
    records=load_records(); scoped=[b for b in records['bids'] if b.get('tender_id')==tender_id]; results=[]
    for index,bid in enumerate(scoped):
        score=max(0, min(100, 70 + min(15, bid.get('experience_years',0)*2) + (10 if bid.get('pan') else 0) + (5 if bid.get('gstin') else 0)))
        risk='LOW' if score>=85 else 'MEDIUM' if score>=70 else 'HIGH'
        bid.update({'score':score,'risk':risk,'status':'REQUIRES_REVIEW','analysis_source':'Rule-Based Fallback','verification_status':'API_UNAVAILABLE'})
        results.append({'bid_id':bid['bid_id'],'bidder_name':bid['bidder_name'],'score':score,'risk':risk,'provider':'Rule-Based Fallback','human_review_required':True,'evidence':[d['name'] for d in bid['documents']]})
    records['analysis'][tender_id]=results; records['audit'].append({'event':'COMPLIANCE_CALCULATED','tender_id':tender_id,'at':now(),'source':'Rule-Based Fallback','human_review_required':True}); save_records(records)
    return {'tender_id':tender_id,'status':'COMPLETED','provider':'Rule-Based Fallback','ollama':'API_UNAVAILABLE','sandbox':'API_UNAVAILABLE','human_review_required':True,'results':results}
@app.get('/api/tenders/{tender_id}/report')
def report(tender_id: str): return {'tender_id':tender_id,'human_review_required':True,'ai_can_decide':False,'analysis':load_records()['analysis'].get(tender_id,[])}
