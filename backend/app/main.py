from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Response, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import hashlib, json, os, re, shutil, tempfile, zipfile, secrets, base64, hmac, urllib.request, urllib.error
try:
    from .ai_pipeline import answer_with_rag, extract_text, verify_documents
except ImportError:  # Supports Uvicorn launched with backend/app as its working directory.
    from ai_pipeline import answer_with_rag, extract_text, verify_documents
SESSION_SECRET = os.getenv('SESSION_SECRET')
if not SESSION_SECRET:
    raise RuntimeError('SESSION_SECRET must be configured')

app = FastAPI(title='SIH26100 TenderHub API', version='2.0.0')
DEFAULT_FRONTEND_ORIGINS = 'https://chatlyme.xyz,https://www.chatlyme.xyz,http://localhost:5173,http://127.0.0.1:5173'
configured_origins = [origin.strip().rstrip('/') for origin in os.getenv('FRONTEND_ORIGINS', DEFAULT_FRONTEND_ORIGINS).split(',') if origin.strip()]
# Keep the deployed UI origins allowed even if a Railway override is incomplete.
# Explicit extra origins can still be supplied through FRONTEND_ORIGINS.
for trusted_origin in ('https://chatlyme.xyz', 'https://www.chatlyme.xyz'):
    if trusted_origin not in configured_origins:
        configured_origins.append(trusted_origin)
if '*' in configured_origins:
    raise RuntimeError('FRONTEND_ORIGINS must list explicit origins when credentials are enabled')
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    # Keep the production web app origins explicitly trusted even when Railway's
    # FRONTEND_ORIGINS value is accidentally incomplete.
    allow_origin_regex=r"^https://(www\.)?chatlyme\.xyz$",
    allow_credentials=True,
    allow_methods=["*"],
    # Multipart document uploads and future API headers must pass preflight.
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)
UPLOADS = Path(os.getenv('UPLOAD_DIR', str(Path(__file__).resolve().parent / 'uploads')))
UPLOADS.mkdir(parents=True, exist_ok=True)
DATA = UPLOADS / 'records.json'
MAX_FILE = 10 * 1024 * 1024
ALLOWED = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'}
DOCUMENT_TYPES = {'TENDER_NOTICE', 'RFP_DOCUMENT', 'TECHNICAL_SPECIFICATIONS', 'SCOPE_OF_WORK', 'ELIGIBILITY_CRITERIA', 'BOQ_PRICE_SCHEDULE', 'TERMS_CONDITIONS', 'EVALUATION_CRITERIA', 'COMPANY_REGISTRATION', 'GST_CERTIFICATE', 'PAN_CARD', 'UDYAM_MSME', 'BANK_DETAILS', 'WORK_EXPERIENCE', 'COMPLETION_CERTIFICATE', 'FINANCIAL_STATEMENT', 'AUDITED_FINANCIALS', 'NON_BLACKLISTING', 'TECHNICAL_PROPOSAL', 'EMD_BID_SECURITY', 'ADDRESS_PROOF', 'OTHER_SUPPORTING'}
MAX_ZIP = 25 * 1024 * 1024

def now(): return datetime.now(timezone.utc).isoformat()

def send_resend_email(to_email: str, subject: str, html: str):
    """Send an optional transactional email; absence/provider failure never breaks a bid."""
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip()
    if not api_key or not from_email or not to_email:
        return {'sent': False, 'reason': 'Resend is not configured'}
    payload = json.dumps({'from': from_email, 'to': [to_email], 'subject': subject, 'html': html}).encode()
    request = urllib.request.Request(
        'https://api.resend.com/emails', data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return {'sent': 200 <= response.status < 300}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # Do not log API keys or block submission/verification on email outages.
        return {'sent': False, 'reason': str(exc)[:200]}

def email_verification_update(application: dict, tender: dict, status: str):
    """Send a concise status email after verification completes."""
    subject = f"TenderHub verification update — {tender.get('name', 'your application')}"
    html = (
        f"<p>Hello {application.get('bidder_name') or application.get('company', {}).get('name', 'Bidder')},</p>"
        f"<p>Document review for <strong>{tender.get('name', 'your tender')}</strong> has finished.</p>"
        f"<p>Status: <strong>{status}</strong></p>"
        f"<p>This is an AI-assisted evidence review, not a legal authenticity determination. "
        f"A procurement officer must complete the final review.</p>"
    )
    return send_resend_email(application.get('email', ''), subject, html)
def load_records():
    if DATA.exists():
        data = json.loads(DATA.read_text())
        data.setdefault('users', []); data.setdefault('bids', []); data.setdefault('tenders', []); data.setdefault('applications', []); data.setdefault('audit', []); data.setdefault('analysis', {}); data.setdefault('decisions', [])
        return data
    return {'users': [], 'bids': [], 'tenders': [], 'applications': [], 'audit': [], 'analysis': {}, 'decisions': []}
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


def set_session_cookie(response: Response, user_id: str):
    secure = os.getenv('COOKIE_SECURE', 'true').strip().lower() == 'true'
    same_site = os.getenv('COOKIE_SAMESITE', 'none').strip().lower()
    if same_site not in {'lax', 'strict', 'none'}:
        same_site = 'none'
    if same_site == 'none' and not secure:
        raise RuntimeError('COOKIE_SECURE must be true when COOKIE_SAMESITE is none')
    response.set_cookie(
        'tenderhub_session', make_session(user_id), httponly=True, secure=secure,
        samesite=same_site, max_age=86400, path='/',
    )


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
def register(response: Response, full_name: str=Form(...), email: str=Form(...), password: str=Form(...), role: str=Form('BIDDER'), organization: str=Form('')):
    full_name = full_name.strip(); email = email.strip().lower(); role = role.strip().upper(); organization = organization.strip()
    if len(full_name) < 2 or len(full_name) > 120: raise HTTPException(422, 'Enter a valid full name')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or len(email) > 254: raise HTTPException(422, 'Enter a valid email address')
    if len(password) < 8 or len(password) > 128: raise HTTPException(422, 'Password must be 8 to 128 characters')
    if role != 'BIDDER': raise HTTPException(422, 'Only bidder accounts can be created')
    if not organization or len(organization) > 160: raise HTTPException(422, 'Organization is required')
    records = load_records(); records.setdefault('users', [])
    if any(u.get('email') == email for u in records['users']): raise HTTPException(409, 'An account with this email already exists')
    user = {'user_id': 'USR-' + secrets.token_hex(8), 'name': full_name, 'email': email, 'role': role, 'organization': organization, 'password_hash': hash_password(password), 'created_at': now()}
    records['users'].append(user); records['audit'].append({'event':'REGISTRATION','user_id':user['user_id'],'role':role,'at':now()}); save_records(records)
    set_session_cookie(response, user['user_id'])
    return public_user(user)

@app.post('/api/auth/login')
def login(response: Response, email: str=Form(...), password: str=Form(...), role: str=Form('')):
    email = email.strip().lower(); role = role.strip().upper()
    records = load_records(); user = next((u for u in records.get('users', []) if u.get('email') == email), None)
    if role and role != 'BIDDER': raise HTTPException(422, 'Only bidder accounts can sign in')
    if not user or user.get('role') != 'BIDDER' or not verify_password(password, user.get('password_hash', '')): raise HTTPException(401, 'Invalid email or password')
    records['audit'].append({'event':'LOGIN','user_id':user['user_id'],'role':user['role'],'at':now()}); save_records(records)
    set_session_cookie(response, user['user_id'])
    return public_user(user)

@app.get('/api/auth/me')
def me(request: Request): return public_user(current_user(request))

@app.post('/api/auth/logout')
def logout(response: Response):
    response.delete_cookie('tenderhub_session')
    return {'status':'logged_out'}

@app.get('/health')
def health():
    upload_path = str(UPLOADS.resolve())
    volume_configured = upload_path == '/data' or upload_path.startswith('/data/')
    return {
        'status': 'ok',
        'mode': 'connected',
        'storage': 'volume_path_configured' if volume_configured else 'ephemeral_storage',
        'ai': {
            'gemini_configured': bool(os.getenv('GEMINI_API_KEY', '').strip()),
            'ollama_configured': bool(os.getenv('OLLAMA_BASE_URL', '').strip()),
        },
        'timestamp': now(),
    }
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
    destination = UPLOADS / folder; destination.mkdir(parents=True, exist_ok=True)
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
            output=[]; destination=UPLOADS/folder; destination.mkdir(parents=True, exist_ok=True)
            for member in members:
                name=safe_name(member.filename); ext=extension(name)
                if ext not in ALLOWED: raise HTTPException(415, f'Unsupported ZIP file: {name}')
                content=z.read(member); digest=hashlib.sha256(content).hexdigest(); stored=f'{digest[:12]}-{name}'
                (destination/stored).write_bytes(content); output.append({'document_id':'DOC-' + secrets.token_hex(8),'name':name,'original_filename':name,'stored_name':stored,'size':len(content),'sha256':digest,'document_type':document_type,'upload_status':'UPLOADED','verification_status':'PENDING','verification_message':'Verification has not started','rag_status':'NOT_STARTED','created_at':now(),'updated_at':now()})
            return {'name':upload.filename or 'documents.zip','status':'EXTRACTED','files':output,'count':len(output)}
    except zipfile.BadZipFile: raise HTTPException(400, 'Invalid ZIP archive')
    finally: shutil.rmtree(temp, ignore_errors=True)

@app.post("/api/tenders")
async def create_tender(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    budget: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),
    department: str = Form("Procurement"),
    requirements: str = Form(""),
    experience: str = Form(""),
    turnover: str = Form(""),
    eligibility_requirements: str = Form(""),
    required_experience: str = Form(""),
    minimum_turnover: str = Form(""),
    bidder_documents: str = Form("[]"),
    terms_conditions: str = Form("[]"),
    category: str = Form("GENERAL"),
    evaluation_method: str = Form("QUALITY_AND_COST"),
    bid_security_required: str = Form("false"),
    bid_security_amount: str = Form(""),
    technical_requirements: str = Form("[]"),
    evaluation_criteria: str = Form("[]"),
    documents: List[UploadFile] = File(default=[]),
    user=Depends(officer_user),
):
    # Validate required fields
    name = name.strip()
    budget = budget.strip()
    description = description.strip()
    deadline = deadline.strip()

    if len(name) < 4:
        raise HTTPException(422, "Tender title must contain at least 4 characters")

    if not budget:
        raise HTTPException(422, "Estimated budget is required")

    if not description:
        raise HTTPException(422, "Description is required")

    if not deadline:
        raise HTTPException(422, "Bid deadline is required")

    # Save uploaded files before confirming publication
    saved_documents = []

    for upload in documents:
        if upload and upload.filename:
            saved_documents.append(
                await store_file(upload, "tenders")
            )

    # Accept both legacy plain-text and current structured frontend fields.
    raw_requirements = eligibility_requirements or requirements
    try:
        parsed_requirements = json.loads(raw_requirements) if raw_requirements.strip().startswith("[") else None
    except json.JSONDecodeError:
        parsed_requirements = None
    if isinstance(parsed_requirements, list):
        requirement_list = [
            str(item.get("text", "")).strip() if isinstance(item, dict) else str(item).strip()
            for item in parsed_requirements
        ]
        requirement_list = [item for item in requirement_list if item]
    else:
        requirement_list = [item.strip() for item in raw_requirements.splitlines() if item.strip()]

    experience = required_experience.strip() or experience.strip()
    turnover = minimum_turnover.strip() or turnover.strip()
    try:
        required_docs = json.loads(bidder_documents or "[]")
        terms = json.loads(terms_conditions or "[]")
        technical = json.loads(technical_requirements or "[]")
        criteria = json.loads(evaluation_criteria or "[]")
        if not isinstance(required_docs, list) or not isinstance(terms, list):
            raise ValueError("Tender documents and terms must be lists")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(422, "Tender document requirements or terms are invalid")

    if experience.strip():
        requirement_list.append(
            f"Minimum experience: {experience.strip()}"
        )

    if turnover.strip():
        requirement_list.append(
            f"Required turnover: {turnover.strip()}"
        )

    tender = {
        "tender_id": (
            f"TND-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        ),
        "name": name,
        "email": user["email"],
        "created_by": user["user_id"],
        "department": department.strip() or "Procurement",
        "budget": budget,
        "description": description,
        "deadline": deadline,
        "experience": experience.strip(),
        "turnover": turnover.strip(),
        "requirements": requirement_list,
        "eligibility_requirements": requirement_list,
        "bidder_documents": required_docs,
        "terms_conditions": terms,
        "category": category,
        "evaluation_method": evaluation_method,
        "bid_security_required": bid_security_required.strip().lower() == "true",
        "bid_security_amount": bid_security_amount.strip(),
        "technical_requirements": technical if isinstance(technical, list) else [],
        "evaluation_criteria": criteria if isinstance(criteria, list) else [],
        "documents": saved_documents,
        "status": "OPEN",
        "bids": 0,
        "created_at": now(),
    }

    records = load_records()
    records.setdefault("tenders", [])
    records.setdefault("audit", [])

    records["tenders"].append(tender)
    records["audit"].append({
        "event": "TENDER_PUBLISHED",
        "tender_id": tender["tender_id"],
        "user_id": user["user_id"],
        "at": now(),
        "documents": len(saved_documents),
    })

    save_records(records)
    background_tasks.add_task(
        send_resend_email,
        user.get('email', ''),
        f"Tender published — {tender.get('name', 'Tender')}",
        f"<p>Your tender <strong>{tender.get('name', 'Tender')}</strong> is now published.</p><p>Budget: {tender.get('budget', 'Not specified')}</p><p>Deadline: {tender.get('deadline', 'See tender details')}</p><p>Bidder applications and document verification status are available in your TenderHub workspace.</p>",
    )

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
    if not query.strip():
        raise HTTPException(422, 'Query is required')
    records = load_records()
    sources = []

    # Tender documents: bidders can query open tenders; officers only their own.
    for tender in records.get('tenders', []):
        allowed = (tender.get('status') == 'OPEN' if user.get('role') == 'BIDDER'
                   else tender.get('email') == user.get('email'))
        if not allowed:
            continue
        for doc in tender.get('documents', []):
            path = UPLOADS / 'tenders' / doc.get('stored_name', '')
            sources.append({
                'name': doc.get('original_filename') or doc.get('name'),
                'document_type': doc.get('document_type'),
                'text': extract_text(path),
            })

    # Application documents: bidders can query their own; officers only applications
    # submitted to tenders they own.
    for app_record in records.get('applications', []):
        tender = next((t for t in records.get('tenders', [])
                       if t.get('tender_id') == app_record.get('tender_id')), None)
        owns_application = (
            app_record.get('bidder_id') == user.get('user_id')
            if user.get('role') == 'BIDDER'
            else bool(tender and tender.get('email') == user.get('email'))
        )
        if not owns_application:
            continue
        for doc in app_record.get('documents', []):
            path = UPLOADS / f"applications/{app_record.get('application_id')}" / doc.get('stored_name', '')
            sources.append({
                'name': doc.get('original_filename') or doc.get('name'),
                'document_type': doc.get('document_type'),
                'text': extract_text(path),
            })

    try:
        return answer_with_rag(query.strip(), sources)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(502, f'RAG request failed: {str(exc)[:300]}')
def application_for(records, application_id, user, allow_officer=False):
    app_record = next((a for a in records.get('applications', []) if a.get('application_id') == application_id), None)
    if not app_record: raise HTTPException(404, 'Application not found')
    if app_record.get('bidder_id') != user.get('user_id') and not (allow_officer and user.get('role') == 'OFFICER'):
        raise HTTPException(403, 'Application access denied')
    return app_record

def tender_for_application(records, tender_id):
    tender = next((t for t in records.get('tenders', []) if t.get('tender_id') == tender_id), None)
    if not tender: raise HTTPException(404, 'Tender not found')
    return tender

@app.get('/api/applications')
def list_applications(user=Depends(bidder_user)):
    return [a for a in load_records().get('applications', []) if a.get('bidder_id') == user['user_id']]

@app.post('/api/applications')
def create_application(payload: dict, user=Depends(bidder_user)):
    records = load_records(); records.setdefault('applications', [])
    tender_id = payload.get('tender_id'); tender = next((t for t in records['tenders'] if t.get('tender_id') == tender_id and t.get('status') == 'OPEN'), None)
    if not tender: raise HTTPException(404, 'Open tender not found')
    existing = next((a for a in records['applications'] if a.get('tender_id') == tender_id and a.get('bidder_id') == user['user_id'] and a.get('status') != 'SUBMITTED'), None)
    if existing:
        existing.update({k: payload[k] for k in ('company','eligibility','accepted_terms','bid_amount') if k in payload}); existing['updated_at'] = now(); save_records(records); return existing
    app_record = {'application_id':'APP-' + secrets.token_hex(8), 'tender_id':tender_id, 'bidder_id':user['user_id'], 'bidder_name':user['name'], 'email':user['email'], 'company':payload.get('company',{}), 'eligibility':payload.get('eligibility',{}), 'documents':[], 'accepted_terms':payload.get('accepted_terms', []), 'bid_amount':payload.get('bid_amount',''), 'status':'DRAFT', 'created_at':now(), 'updated_at':now()}
    records['applications'].append(app_record); records['audit'].append({'event':'APPLICATION_DRAFT_CREATED','application_id':app_record['application_id'],'user_id':user['user_id'],'at':now()}); save_records(records); return app_record

@app.put('/api/applications/{application_id}')
def update_application(application_id: str, payload: dict, user=Depends(bidder_user)):
    records=load_records(); item=application_for(records, application_id, user)
    if item.get('status') == 'SUBMITTED': raise HTTPException(409, 'Submitted applications cannot be edited')
    for key in ('company','eligibility','accepted_terms','bid_amount'):
        if key in payload: item[key]=payload[key]
    item['updated_at']=now(); save_records(records); return item

@app.post('/api/applications/{application_id}/documents')
async def application_document(application_id: str, file: UploadFile=File(...), document_type: str=Form(...), user=Depends(bidder_user)):
    records=load_records(); item=application_for(records, application_id, user)
    if item.get('status') == 'SUBMITTED': raise HTTPException(409, 'Submitted applications cannot be edited')
    result=await store_file(file, f'applications/{application_id}', document_type)
    result['bidder_id']=user['user_id']; result['application_id']=application_id; result['tender_id']=item['tender_id']; result['verification_status']='NOT_STARTED'; result['rag_status']='PROCESSING'
    item['documents']=[d for d in item.get('documents',[]) if d.get('document_type') != document_type] + [result]; item['updated_at']=now(); save_records(records); return {k:v for k,v in result.items() if k not in ('stored_name','sha256')}

@app.get('/api/applications/{application_id}/documents/{document_id}')
def protected_document(application_id: str, document_id: str, user=Depends(current_user)):
    records=load_records(); item=application_for(records, application_id, user, allow_officer=True)
    if user.get('role') == 'OFFICER':
        tender = tender_for_application(records, item.get('tender_id'))
        if tender.get('email') != user.get('email'):
            raise HTTPException(403, 'Document access denied for this tender')
    doc=next((d for d in item.get('documents',[]) if d.get('document_id')==document_id),None)
    if not doc: raise HTTPException(404,'Document not found')
    path=UPLOADS / f'applications/{application_id}' / doc.get('stored_name','')
    if not path.exists(): raise HTTPException(404,'Stored document not found')
    from fastapi.responses import FileResponse
    return FileResponse(path, filename=doc.get('original_filename',doc.get('name','document')))

def run_application_verification(application_id: str):
    """Background verification so submitting bidders do not wait for the Gemini API."""
    records = load_records()
    item = next((a for a in records.get('applications', [])
                 if a.get('application_id') == application_id), None)
    if not item or item.get('status') != 'SUBMITTED':
        return
    tender = next((t for t in records.get('tenders', [])
                   if t.get('tender_id') == item.get('tender_id')), None)
    if not tender:
        item['verification_status'] = 'REQUIRES_MANUAL_REVIEW'
        item['verification_message'] = 'Tender record was not found.'
        save_records(records)
        return
    try:
        result = verify_documents(item, tender, UPLOADS)
        item['documents'] = result.pop('documents', item.get('documents', []))
        item['ai_review'] = result
        verification_status = result.get('overall_status') or result.get('status') or 'REQUIRES_MANUAL_REVIEW'
        item['verification_status'] = verification_status
        item['ai_review_status'] = 'COMPLETED' if verification_status != 'REQUIRES_MANUAL_REVIEW' else 'REQUIRES_MANUAL_REVIEW'
        item['verification_completed_at'] = now()
        provider = result.get('provider', 'NONE')
    except Exception as exc:
        # A provider/network/parse error must not leave the application permanently pending.
        item['verification_status'] = 'REQUIRES_MANUAL_REVIEW'
        item['ai_review_status'] = 'FAILED_REQUIRES_MANUAL_REVIEW'
        item['verification_message'] = f'Automated verification failed; officer review is required. {str(exc)[:250]}'
        item['verification_completed_at'] = now()
        provider = 'NONE'
        for document in item.get('documents', []):
            document['verification_status'] = 'REQUIRES_MANUAL_REVIEW'
            document['verification_message'] = 'Automated verification failed; officer review is required.'
    records.setdefault('audit', []).append({
        'event': 'DOCUMENT_VERIFICATION_COMPLETED',
        'application_id': application_id,
        'verification_status': item['verification_status'],
        'at': now(),
        'provider': provider,
    })
    save_records(records)
    email_verification_update(item, tender, item['verification_status'])


@app.get('/api/applications/{application_id}')
def get_application(application_id: str, user=Depends(bidder_user)):
    records = load_records()
    item = application_for(records, application_id, user)
    # Do not expose internal storage paths or hashes to the bidder.
    return {**item, 'documents': [
        {k: v for k, v in doc.items() if k not in ('stored_name', 'sha256')}
        for doc in item.get('documents', [])
    ]}


@app.post('/api/applications/{application_id}/submit')
def submit_application(application_id: str, request: Request, background_tasks: BackgroundTasks, user=Depends(bidder_user)):
    records=load_records(); item=application_for(records, application_id, user)
    idempotency_key = request.headers.get('Idempotency-Key', '').strip()
    if item.get('status') == 'SUBMITTED':
        # The browser can lose its connection after the server commits the submission.
        # Return the existing receipt on retry instead of creating duplicate submissions.
        return {'application_id':application_id,'confirmation_number':item.get('confirmation_number'),'status':'SUBMITTED','verification_status':item.get('verification_status','PENDING_VERIFICATION'),'idempotent_replay':True}
    company=item.get('company',{}); required=['name','authorized_person','email','mobile','city','experience_years','annual_turnover','pan','gstin']
    if any(not str(company.get(k,'')).strip() for k in required) or not item.get('bid_amount'): raise HTTPException(422,'Required company and bid fields are incomplete')
    if not all(item.get('eligibility',{}).get(k) for k in ('experience_confirmation','turnover_confirmation','compliance_declaration')): raise HTTPException(422,'Eligibility confirmations are incomplete')
    tender = tender_for_application(records, item.get('tender_id'))
    tender_docs = tender.get('bidder_documents', [])
    required_doc_rows = [
        d for d in tender_docs
        if d.get('document_type')
        and d.get('required', True) is not False
        and str(d.get('required', True)).strip().lower() not in {'false', '0', 'no'}
    ]
    # Compare normalized types so casing/whitespace differences cannot make a
    # successfully uploaded document look missing.
    required_docs = {
        str(d.get('document_type', '')).strip().upper()
        for d in required_doc_rows
    }
    uploaded = {
        str(d.get('document_type', '')).strip().upper()
        for d in item.get('documents', [])
        if str(d.get('upload_status', '')).strip().upper() == 'UPLOADED'
    }
    missing_docs = required_docs - uploaded
    if missing_docs:
        missing_labels = [
            str(d.get('name') or d.get('document_type')).strip()
            for d in required_doc_rows
            if str(d.get('document_type', '')).strip().upper() in missing_docs
        ]
        raise HTTPException(
            422,
            'Required documents are incomplete. Upload: ' + ', '.join(missing_labels)
        )
    required_terms={str(term.get('id') or term.get('text')) for term in tender.get('terms_conditions', [])}
    accepted={str(term) for term in item.get('accepted_terms', [])}
    if required_terms and not required_terms.issubset(accepted): raise HTTPException(422,'All tender terms must be accepted')
    item['status']='SUBMITTED'; item['submitted_at']=now(); item['verification_status']='PENDING_VERIFICATION'; item['confirmation_number']='TH-' + secrets.token_hex(6).upper(); item['submission_idempotency_key']=idempotency_key or secrets.token_urlsafe(18); item['verification_jobs']=[{'status':'QUEUED','queued_at':now()}]; records['audit'].append({'event':'APPLICATION_SUBMITTED','application_id':application_id,'user_id':user['user_id'],'at':now(),'verification_status':'PENDING_VERIFICATION'}); save_records(records)
    background_tasks.add_task(run_application_verification, application_id)
    background_tasks.add_task(
        send_resend_email,
        item.get('email', ''),
        f"TenderHub bid received — {tender.get('name', 'Tender')}",
        f"<p>Your bid has been received for <strong>{tender.get('name', 'the tender')}</strong>.</p><p>Confirmation: <strong>{item['confirmation_number']}</strong></p><p>Deadline: {tender.get('deadline', 'see tender details')}</p><p>Document verification is now queued. Final decisions require officer review.</p>",
    )
    return {'application_id':application_id,'confirmation_number':item['confirmation_number'],'status':'SUBMITTED','verification_status':'PENDING_VERIFICATION','message':'Application submitted. Document verification has started in the background.'}

def owned_tender(records, tender_id, user):
    tender = next((t for t in records.get('tenders', []) if t.get('tender_id') == tender_id), None)
    if not tender: raise HTTPException(404, 'Tender not found')
    if tender.get('email') != user.get('email'): raise HTTPException(403, 'Tender review access denied')
    return tender

def application_public(item):
    # Officer UI gets document metadata but never internal storage paths or hashes.
    public = {k: v for k, v in item.items() if k not in ('bidder_id', 'submission_idempotency_key')}
    public['documents'] = [
        {k: v for k, v in doc.items() if k not in ('stored_name', 'sha256', 'extracted_text_preview')}
        for doc in item.get('documents', [])
    ]
    return public

@app.get('/api/officer/bids')
def officer_bids(user=Depends(officer_user)):
    records = load_records(); result=[]
    for item in records.get('applications', []):
        tender = next((t for t in records.get('tenders', []) if t.get('tender_id') == item.get('tender_id')), None)
        if tender and tender.get('email') == user.get('email'):
            result.append({**application_public(item), 'tender_title': tender.get('name'), 'department': tender.get('department'), 'deadline': tender.get('deadline'), 'document_verification_status': item.get('verification_status', 'PENDING_VERIFICATION' if item.get('documents') else 'DOCUMENTS_PENDING'), 'ai_review_status': item.get('ai_review_status', 'NOT_STARTED')})
    return result

@app.get('/api/bids/{application_id}')
def officer_bid(application_id: str, user=Depends(officer_user)):
    records=load_records(); item=application_for(records, application_id, user, allow_officer=True); owned_tender(records, item.get('tender_id'), user)
    tender=next(t for t in records['tenders'] if t.get('tender_id') == item.get('tender_id'))
    return {'application': application_public(item), 'tender': {k:v for k,v in tender.items() if k != 'documents'}}

@app.get('/api/bids/{application_id}/documents')
def officer_bid_documents(application_id: str, user=Depends(officer_user)):
    records=load_records(); item=application_for(records, application_id, user, allow_officer=True); owned_tender(records, item.get('tender_id'), user)
    return [{k:v for k,v in d.items() if k not in ('stored_name','sha256')} for d in item.get('documents', [])]

@app.post('/api/bids/{application_id}/ai-review')
def ai_review(application_id: str, user=Depends(officer_user)):
    records=load_records()
    item=application_for(records, application_id, user, allow_officer=True)
    tender=owned_tender(records, item.get('tender_id'), user)
    result=verify_documents(item, tender, UPLOADS)
    item['documents']=result.pop('documents', item.get('documents', []))
    item['ai_review']=result
    item['verification_status']=result.get('status', 'REQUIRES_MANUAL_REVIEW')
    item['ai_review_status']='COMPLETED' if result.get('status') != 'REQUIRES_MANUAL_REVIEW' else 'REQUIRES_MANUAL_REVIEW'
    item['verification_completed_at']=now()
    records['audit'].append({'event':'AI_REVIEW_COMPLETED','application_id':application_id,'user_id':user['user_id'],'at':now(),'verification_status':item['verification_status']})
    save_records(records)
    return result

@app.post('/api/tenders/{tender_id}/award')
def award_tender(tender_id: str, application_id: str = Form(...), user=Depends(officer_user)):
    records=load_records(); tender=owned_tender(records, tender_id, user)
    if tender.get('status') == 'AWARDED': raise HTTPException(409, 'Tender has already been awarded')
    item=application_for(records, application_id, user, allow_officer=True)
    if item.get('tender_id') != tender_id: raise HTTPException(422, 'Application does not belong to this tender')
    if item.get('status') != 'SUBMITTED': raise HTTPException(409, 'Only submitted applications can be awarded')
    tender['status']='AWARDED'; item['status']='AWARDED'; item['awarded_at']=now(); item['notification_status']='PENDING'
    for other in records.get('applications', []):
        if other.get('tender_id') == tender_id and other.get('application_id') != application_id and other.get('status') == 'SUBMITTED': other['status']='NOT_SELECTED'
    records['audit'].append({'event':'TENDER_AWARDED','tender_id':tender_id,'application_id':application_id,'user_id':user['user_id'],'at':now()}); save_records(records)
    return {'status':'AWARDED','tender_id':tender_id,'application_id':application_id,'notification_status':'PENDING','awarded_at':item['awarded_at']}

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
def report(tender_id: str, user=Depends(officer_user)):
    records = load_records(); owned_tender(records, tender_id, user)
    return {'tender_id':tender_id,'human_review_required':True,'ai_can_decide':False,'analysis':records['analysis'].get(tender_id,[])}

@app.get('/api/bids/{application_id}/analysis')
def application_analysis(application_id: str, user=Depends(officer_user)):
    records=load_records(); item=application_for(records, application_id, user, allow_officer=True); owned_tender(records, item['tender_id'], user)
    return item.get('ai_review') or {'status':'PENDING','message':'Analysis has not been requested.','human_review_required':True}

@app.post('/api/bids/{application_id}/decision')
def decide_application(application_id: str, decision: str=Form(...), remarks: str=Form(''), user=Depends(officer_user)):
    records=load_records(); item=application_for(records, application_id, user, allow_officer=True); tender=owned_tender(records, item['tender_id'], user)
    decision=decision.strip().upper()
    if decision not in {'SHORTLISTED','REJECTED','CLARIFICATION_REQUESTED'}: raise HTTPException(422,'Decision must be SHORTLISTED, REJECTED, or CLARIFICATION_REQUESTED')
    if item.get('status') not in {'SUBMITTED','SHORTLISTED','CLARIFICATION_REQUESTED'}: raise HTTPException(409,'Only submitted applications can receive a decision')
    item['status']=decision; item['officer_remarks']=remarks.strip(); item['decision_at']=now(); item['decision_by']=user['user_id']
    event={'event':'BID_DECISION','application_id':application_id,'tender_id':tender['tender_id'],'user_id':user['user_id'],'decision':decision,'at':item['decision_at']}
    records.setdefault('decisions',[]).append(event); records['audit'].append(event); save_records(records)
    return {'application_id':application_id,'tender_id':tender['tender_id'],'status':decision,'remarks':item['officer_remarks'],'notification_status':'NOT_SENT'}

@app.delete('/api/applications/{application_id}/documents/{document_id}')
def remove_application_document(application_id: str, document_id: str, user=Depends(bidder_user)):
    records=load_records(); item=application_for(records, application_id, user)
    if item.get('status')=='SUBMITTED': raise HTTPException(409,'Submitted applications cannot be edited')
    doc=next((d for d in item.get('documents',[]) if d.get('document_id')==document_id),None)
    if not doc: raise HTTPException(404,'Document not found')
    path=UPLOADS / f'applications/{application_id}' / doc.get('stored_name','')
    if path.exists(): path.unlink()
    item['documents']=[d for d in item['documents'] if d.get('document_id')!=document_id]; item['updated_at']=now(); save_records(records)
    return {'document_id':document_id,'removed':True}
