from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import hashlib, json, os, re, shutil, tempfile, zipfile, secrets, base64, hmac
SESSION_SECRET = os.getenv('SESSION_SECRET')
if not SESSION_SECRET:
    raise RuntimeError('SESSION_SECRET must be configured')

app = FastAPI(title='SIH26100 TenderHub API', version='2.0.0')
configured_origins = [origin.strip() for origin in os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173').split(',') if origin.strip()]
if '*' in configured_origins:
    raise RuntimeError('FRONTEND_ORIGINS must list explicit origins when credentials are enabled')
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials='*' not in configured_origins,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)
UPLOADS = Path(os.getenv('UPLOAD_DIR', str(Path(__file__).resolve().parent / 'uploads')))
UPLOADS.mkdir(parents=True, exist_ok=True)
DATA = UPLOADS / 'records.json'
MAX_FILE = 10 * 1024 * 1024
ALLOWED = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'}
DOCUMENT_TYPES = {'TENDER_NOTICE', 'COMPANY_REGISTRATION', 'GST_CERTIFICATE', 'PAN_CARD', 'BANK_DETAILS', 'WORK_EXPERIENCE', 'FINANCIAL_STATEMENT', 'TECHNICAL_DOCUMENT', 'OTHER_SUPPORTING'}
MAX_ZIP = 25 * 1024 * 1024

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

def hash_password(password: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210000)
    return base64.b64encode(salt).decode() + ':' + base64.b64encode(digest).decode()

def make_session(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({'user_id': user_id, 'exp': int(datetime.now(timezone.utc).timestamp()) + 86400}).encode()).decode()
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + '.' + signature

def current_user(request: Request):
    token = request.cookies.get('tenderhub_session')
    if not token or '.' not in token: raise HTTPException(401, 'Authentication required')
    payload, signature = token.rsplit('.', 1)
    expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected): raise HTTPException(401, 'Invalid session')
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        if data['exp'] < int(datetime.now(timezone.utc).timestamp()): raise HTTPException(401, 'Session expired')
    except (ValueError, KeyError, json.JSONDecodeError): raise HTTPException(401, 'Invalid session')
    user = next((u for u in load_records().get('users', []) if u['user_id'] == data['user_id']), None)
    if not user: raise HTTPException(401, 'User not found')
    return user

def public_user(user): return {k: user.get(k, '') for k in ('user_id','name','email','role','organization')}


def officer_user(user=Depends(current_user)):
    if user['role'] != 'OFFICER': raise HTTPException(403, 'Officer access required')
    return user


def bidder_user(user=Depends(current_user)):
    if user['role'] != 'BIDDER': raise HTTPException(403, 'Bidder access required')
    return user
def require_role(role: str):
    def checker(user=Depends(current_user)):
        if user['role'] != role: raise HTTPException(403, 'Insufficient permissions')
        return user
    return checker

def verify_password(password: str, stored: str):
    try:
        salt, expected = stored.split(':', 1)
        actual = hash_password(password, base64.b64decode(salt)).split(':', 1)[1]
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

@app.post('/api/auth/register')
def register(response: Response, full_name: str=Form(...), email: str=Form(...), password: str=Form(...), role: str=Form('OFFICER'), organization: str=Form('')):
    if len(password) < 8: raise HTTPException(422, 'Password must be at least 8 characters')
    email = email.strip().lower(); records = load_records(); records.setdefault('users', [])
    if any(u['email'] == email for u in records['users']): raise HTTPException(409, 'An account with this email already exists')
    user = {'user_id': 'USR-' + secrets.token_hex(8), 'name': full_name.strip(), 'email': email, 'role': role if role in {'OFFICER','BIDDER'} else 'BIDDER', 'organization': organization.strip(), 'password_hash': hash_password(password), 'created_at': now()}
    records['users'].append(user); records['audit'].append({'event':'REGISTRATION','user_id':user['user_id'],'at':now()}); save_records(records)
    response.set_cookie('tenderhub_session', make_session(user['user_id']), httponly=True, secure=os.getenv('COOKIE_SECURE','true').lower() == 'true', samesite=os.getenv('COOKIE_SAMESITE', 'none'), max_age=86400)
    return public_user(user)

@app.post('/api/auth/login')
def login(response: Response, email: str=Form(...), password: str=Form(...)):
    records = load_records(); user = next((u for u in records.get('users', []) if u['email'] == email.strip().lower()), None)
    if not user or not verify_password(password, user['password_hash']): raise HTTPException(401, 'Invalid email or password')
    records['audit'].append({'event':'LOGIN','user_id':user['user_id'],'at':now()}); save_records(records)
    response.set_cookie('tenderhub_session', make_session(user['user_id']), httponly=True, secure=os.getenv('COOKIE_SECURE','true').lower() == 'true', samesite=os.getenv('COOKIE_SAMESITE', 'none'), max_age=86400)
    return public_user(user)

@app.get('/api/auth/me')
def me(request: Request): return public_user(current_user(request))

@app.post('/api/auth/logout')
def logout(response: Response):
    response.delete_cookie('tenderhub_session')
    return {'status':'logged_out'}

@app.get('/health')
def health(): return {'status':'ok','mode':'connected','storage':'configured persistence','timestamp':now()}
@app.get('/api/tenders')
def tenders(user=Depends(current_user)):
    return load_records()['tenders'] if user['role'] == 'OFFICER' else [t for t in load_records()['tenders'] if t.get('status') == 'OPEN']

@app.get('/api/bids')
def bids(user=Depends(current_user)):
    records = load_records()
    return records['bids'] if user['role'] == 'OFFICER' else [b for b in records['bids'] if b.get('email') == user['email']]

@app.get('/api/audit')
def get_audit(user=Depends(officer_user)):
    return load_records()['audit']

async def store_file(upload: UploadFile, folder: str, document_type: str = 'OTHER_SUPPORTING'):
    name = safe_name(upload.filename); ext = extension(name)
    document_type = document_type.upper()
    if document_type not in DOCUMENT_TYPES: raise HTTPException(422, 'Invalid document type')
    if ext == 'zip': return await store_zip(upload, folder, document_type)
    if ext not in ALLOWED: raise HTTPException(415, 'Accepted formats: PDF, DOC, DOCX, XLS, XLSX, JPG, JPEG, PNG and ZIP')
    data = await upload.read()
    if len(data) > MAX_FILE: raise HTTPException(413, 'File exceeds 10 MB limit')
    destination = UPLOADS / folder; destination.mkdir(exist_ok=True)
    unique = f'{hashlib.sha256(data).hexdigest()[:12]}-{name}'
    path = destination / unique; path.write_bytes(data)
    return {'document_id':'DOC-' + secrets.token_hex(8),'name':name,'original_filename':name,'stored_name':unique,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'document_type':document_type,'upload_status':'UPLOADED','verification_status':'PENDING','verification_message':'Verification has not started','rag_status':'NOT_STARTED','created_at':now(),'updated_at':now()}

async def store_zip(upload: UploadFile, folder: str, document_type: str = 'OTHER_SUPPORTING'):
    data = await upload.read()
    if len(data) > 25 * 1024 * 1024: raise HTTPException(413, 'ZIP exceeds 25 MB limit')
    if not zipfile.is_zipfile(__import__('io').BytesIO(data)):
        raise HTTPException(400, 'Invalid ZIP archive')
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
                (destination/stored).write_bytes(content); output.append({'document_id':'DOC-' + secrets.token_hex(8),'name':name,'original_filename':name,'stored_name':stored,'size':len(content),'sha256':digest,'document_type':document_type,'upload_status':'UPLOADED','verification_status':'PENDING','verification_message':'Verification has not started','rag_status':'NOT_STARTED','created_at':now(),'updated_at':now()})
            return {'name':upload.filename or 'documents.zip','status':'EXTRACTED','files':output,'count':len(output)}
    except zipfile.BadZipFile: raise HTTPException(400, 'Invalid ZIP archive')
    finally: shutil.rmtree(temp, ignore_errors=True)

@app.post('/api/tenders')
async def create_tender(
    name: str = Form(...),
    experience: str = Form(...),
    budget: str = Form(...),
    description: str = Form(...),
    department: str = Form('Procurement'),
    deadline: str = Form(...),
    turnover: str = Form(''),
    documents: List[UploadFile] = File(default=[]),
    user=Depends(officer_user),
):
    name = name.strip()
    experience = experience.strip()
    budget = budget.strip()
    description = description.strip()
    department = department.strip()
    deadline = deadline.strip()
    turnover = turnover.strip()

    if len(name) < 4:
        raise HTTPException(422, 'Tender title is required')

    saved = []

    for upload in documents:
        if upload and upload.filename:
            saved.append(await store_file(upload, 'tenders'))

    tender = {
        'tender_id': f'TND-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'name': name,
        'email': user['email'],
        'experience': experience,
        'turnover': turnover,
        'budget': budget,
        'description': description,
        'department': department,
        'deadline': deadline,
        'documents': saved,
        'requirements': [
            'Minimum experience: ' + experience,
            'Required turnover: ' + turnover
            if turnover
            else 'Turnover review required',
        ],
        'status': 'OPEN',
        'bids': 0,
        'created_at': now(),
    }

    records = load_records()
    records['tenders'].append(tender)
    records['audit'].append({
        'event': 'TENDER_PUBLISHED',
        'tender_id': tender['tender_id'],
        'at': now(),
        'documents': len(saved),
    })

    save_records(records)

    return tender
@app.post('/api/bids')
async def create_bid(tender_id: str=Form(...), name: str=Form(...), email: str=Form(...), city: str=Form(...), experience: int=Form(...), bid_amount: str=Form(''), pan: str=Form(''), gstin: str=Form(''), declaration: str=Form(...), documents: List[UploadFile]=File(default=[]), user=Depends(bidder_user)):
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
async def upload(file: UploadFile=File(...), document_type: str=Form('OTHER_SUPPORTING'), user=Depends(current_user)):
    folder = 'tenders' if user['role'] == 'OFFICER' else 'bids'
    result = await store_file(file, folder, document_type)
    records = load_records(); records['audit'].append({'event':'DOCUMENT_UPLOADED','document_id':result.get('document_id'),'document_type':document_type.upper(),'user_id':user['user_id'],'at':now()}); save_records(records)
    return result

@app.get('/api/documents/{document_id}/status')
def document_status(document_id: str, user=Depends(current_user)):
    for collection in ('tenders', 'bids'):
        for record in load_records().get(collection, []):
            for document in record.get('documents', []):
                if document.get('document_id') == document_id:
                    return document
    raise HTTPException(404, 'Document not found')

@app.post('/api/documents/{document_id}/verify')
def verify_document(document_id: str, user=Depends(current_user)):
    if not os.getenv('SANDBOX_API_KEY'):
        return {'document_id':document_id,'verification_status':'REQUIRES_MANUAL_REVIEW','verification_message':'Sandbox credentials are not configured; no verification was claimed.','provider':'SANDBOX','real_result':False}
    return {'document_id':document_id,'verification_status':'PENDING','verification_message':'Verification provider is configured; processing is pending.','provider':'SANDBOX','real_result':True}

@app.post('/api/rag/query')
def rag_query(query: str=Form(...), user=Depends(current_user)):
    if not query.strip(): raise HTTPException(422, 'Query is required')
    raise HTTPException(503, 'RAG processing is unavailable until an embedding and vector provider is configured')
@app.post('/api/tenders/{tender_id}/analyze-bidders')
def analyze(tender_id: str, user=Depends(officer_user)):
    records=load_records(); scoped=[b for b in records['bids'] if b.get('tender_id')==tender_id]; results=[]
    for index,bid in enumerate(scoped):
        score=max(0, min(100, 70 + min(15, bid.get('experience_years',0)*2) + (10 if bid.get('pan') else 0) + (5 if bid.get('gstin') else 0)))
        risk='LOW' if score>=85 else 'MEDIUM' if score>=70 else 'HIGH'
        bid.update({'score':score,'risk':risk,'status':'REQUIRES_REVIEW','analysis_source':'Rule-Based Fallback','verification_status':'API_UNAVAILABLE'})
        results.append({'bid_id':bid['bid_id'],'bidder_name':bid['bidder_name'],'score':score,'risk':risk,'provider':'Rule-Based Fallback','human_review_required':True,'evidence':[d['name'] for d in bid['documents']]})
    records['analysis'][tender_id]=results; records['audit'].append({'event':'COMPLIANCE_CALCULATED','tender_id':tender_id,'at':now(),'source':'Rule-Based Fallback','human_review_required':True}); save_records(records)
    return {'tender_id':tender_id,'status':'COMPLETED','provider':'Rule-Based Fallback','ollama':'API_UNAVAILABLE','sandbox':'API_UNAVAILABLE','human_review_required':True,'results':results}
@app.get('/api/tenders/{tender_id}/report')
def report(tender_id: str, user=Depends(officer_user)): return {'tender_id':tender_id,'human_review_required':True,'ai_can_decide':False,'analysis':load_records()['analysis'].get(tender_id,[])}
