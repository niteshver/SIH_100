You are a senior full-stack architect, Python developer, React developer, AI engineer, DevOps engineer, and hackathon MVP specialist.

Build a complete working MVP for Smart India Hackathon 2026 Software Problem Statement SIH26100.

==================================================
1. PROJECT INFORMATION
==================================================

Problem Statement ID:
SIH26100

Problem Statement:
AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement

Organization:
Ministry of Petroleum & Natural Gas

Department:
Chennai Petroleum Corporation Limited (CPCL)

Category:
Software

Theme:
Smart Automation

==================================================
2. CORE PROBLEM
==================================================

Government procurement through GeM requires procurement officers to manually examine many bidder documents and verify statutory, regulatory, and tender-specific requirements.

Examples include:

- PAN
- GST
- Udyam/MSME
- Income Tax
- MCA/company registration
- Startup India
- NSIC
- EPFO
- ESIC
- DigiLocker
- Make in India/local content
- BIS/DPIIT
- OEM authorization
- Blacklisting/debarment
- Experience certificates
- Financial documents
- Other tender-specific requirements

The current process is document-heavy and requires cross-checking information across multiple sources.

This causes:

- High manual effort
- Slow tender evaluation
- Human errors
- Inconsistent verification
- Difficulty identifying discrepancies
- Difficulty maintaining an audit trail

==================================================
3. PROJECT OBJECTIVE
==================================================

Build an AI-powered Bid Compliance Verification Platform that helps a Procurement Officer evaluate multiple bidders.

The platform must:

1. Create/manage tenders.
2. Upload tender requirement documents.
3. Extract tender requirements using document processing and AI.
4. Create/manage bidders.
5. Allow bidders to submit required documents.
6. Automatically identify uploaded documents.
7. Extract structured information from documents.
8. Validate document fields and formats.
9. Check mandatory tender requirements.
10. Cross-check information across bidder documents.
11. Compare bidder evidence with tender requirements.
12. Detect missing information.
13. Detect inconsistent information.
14. Generate risk indicators.
15. Calculate a compliance score.
16. Generate AI explanations/recommendations.
17. Provide a procurement dashboard.
18. Maintain an audit trail.
19. Allow the Procurement Officer to make the final decision.

IMPORTANT:

The AI must NEVER automatically make the final qualification/disqualification decision.

The final decision belongs to the Procurement Officer.

The system is a decision-support and verification platform.

==================================================
4. IMPORTANT HACKATHON STRATEGY
==================================================

Do NOT make the MVP dependent on real government APIs.

Government APIs may:

- Require approval
- Require credentials
- Be unavailable
- Have rate limits
- Be paid
- Be difficult to access during a hackathon

Therefore build the system using a PROVIDER/ADAPTER architecture.

Example:

VerificationProvider
    |
    +-- MockVerificationProvider
    |
    +-- CashfreeVerificationProvider
    |
    +-- FutureGovernmentAPIProvider

For the hackathon:

MockVerificationProvider MUST be fully functional.

The UI should clearly show:

"Demo Verification Source"

or

"Mock Government Verification"

Do not falsely claim that mock data came from an actual government portal.

The architecture must allow real government APIs to be plugged in later without rewriting the compliance engine.

==================================================
5. HIGH LEVEL SYSTEM
==================================================

The complete system should look like:

                    PROCUREMENT OFFICER
                           |
                           v
                    React Web Application
                           |
                           v
                       FastAPI
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
     PostgreSQL       Document Engine    AI Engine
          |                |                |
          |                v                |
          |          OCR + Extraction       |
          |                |                |
          |                v                |
          |        Structured JSON          |
          |                |                |
          +----------------+----------------+
                           |
                           v
                  Compliance Engine
                           |
              +------------+------------+
              |            |            |
              v            v            v
         Rule Engine   RAG Engine    Risk Engine
              |            |            |
              +------------+------------+
                           |
                           v
                  Local LLM / Ollama
                           |
                           v
                 Compliance Report
                           |
                           v
                  Procurement Officer
                           |
                           v
                  Final Human Decision

==================================================
6. TECHNOLOGY STACK
==================================================

Use the following stack.

--------------------
FRONTEND
--------------------

React
Vite
TypeScript
Tailwind CSS
shadcn/ui
Framer Motion
React Router
TanStack Query
Axios
Lucide Icons

--------------------
BACKEND
--------------------

Python 3.12+

FastAPI
Pydantic
SQLAlchemy
Alembic
Uvicorn

--------------------
DATABASE
--------------------

PostgreSQL

Use pgvector if possible.

PostgreSQL should store:

- Users
- Tenders
- Tender requirements
- Bidders
- Bids
- Documents
- Extracted fields
- Validation results
- Verification results
- Risk assessments
- AI reports
- Audit logs

--------------------
AI / LLM
--------------------

Ollama

The system must support local LLM inference.

Do not hard-code a specific model.

Use:

OLLAMA_BASE_URL
OLLAMA_MODEL

from environment variables.

Recommended architecture:

LLMProvider
    |
    +-- OllamaProvider
    |
    +-- MockLLMProvider

This is important because Railway cannot directly access Ollama running on a developer's local Mac.

Local development:

Ollama -> localhost:11434

Railway demo:

Use MockLLMProvider OR a separately hosted inference service.

Never expose the developer's local Ollama server publicly.

--------------------
DOCUMENT PROCESSING
--------------------

PyMuPDF
Pillow
OpenCV

OCR:

PaddleOCR

Build the OCR layer so it can later support other OCR engines.

--------------------
RAG
--------------------

LangChain

Use LangChain for:

- Document loading
- Text splitting
- Embeddings
- Retrieval
- Vector database integration
- LLM abstraction

Use RAG mainly for:

Tender requirement documents
and
Bidder evidence/document text.

--------------------
WORKFLOW
--------------------

LangGraph

Use LangGraph to represent the verification workflow.

Example:

START
  |
  v
Load Tender
  |
  v
Load Bidder Documents
  |
  v
Document Classification
  |
  v
OCR / Text Extraction
  |
  v
Structured Data Extraction
  |
  v
Field Validation
  |
  v
Tender Requirement Matching
  |
  v
RAG Evidence Retrieval
  |
  v
Cross Document Comparison
  |
  v
External/Mock Verification
  |
  v
Risk Calculation
  |
  v
LLM Analysis
  |
  v
Compliance Report
  |
  v
Human Review
  |
  v
END

--------------------
STORAGE
--------------------

For MVP:

Local filesystem:

backend/uploads/

Structure:

uploads/
    tenders/
    bidders/
    processed/

Later:

S3 / Cloudflare R2 / Supabase Storage.

--------------------
DEPLOYMENT
--------------------

Frontend:

Vercel OR Railway

Backend:

Railway

Database:

Railway PostgreSQL

Containerization:

Docker

CI/CD:

GitHub Actions

==================================================
7. PROJECT STRUCTURE
==================================================

Create a clean monorepo.

project-root/

    frontend/

        src/
            components/
            pages/
            layouts/
            hooks/
            services/
            types/
            utils/
            lib/

        public/

        package.json
        vite.config.ts
        tsconfig.json
        tailwind.config.js

        Dockerfile
        nginx.conf

    backend/

        app/

            main.py

            api/
                auth.py
                tenders.py
                bidders.py
                bids.py
                documents.py
                verification.py
                reports.py
                audit.py
                health.py

            models/
                user.py
                tender.py
                tender_requirement.py
                bidder.py
                bid.py
                document.py
                extracted_data.py
                validation.py
                verification.py
                risk.py
                report.py
                audit.py

            schemas/
                tender.py
                bidder.py
                bid.py
                document.py
                verification.py
                report.py

            services/

                ocr_service.py

                document_classifier.py

                document_parser.py

                extraction_service.py

                validation_engine.py

                requirement_engine.py

                compliance_engine.py

                comparison_engine.py

                risk_engine.py

                rag_service.py

                llm_service.py

                report_service.py

                audit_service.py

            integrations/

                verification_provider.py

                mock_provider.py

                cashfree_provider.py

            ai/

                prompts/
                chains/
                graphs/

            db/
                database.py
                session.py

            core/
                config.py
                security.py
                logging.py

            utils/

        migrations/

        tests/

        requirements.txt

        Dockerfile

        .env.example

    docker-compose.yml

    .github/
        workflows/
            ci.yml

    README.md

    .gitignore

    .dockerignore

==================================================
8. USER ROLES
==================================================

MVP should support:

1. Procurement Officer
2. Bidder

Authentication can be simplified for MVP.

Use seeded/demo users if full authentication is not necessary.

However design the database so proper authentication can be added later.

==================================================
9. PROCUREMENT OFFICER FLOW
==================================================

The Procurement Officer should be able to:

1. Open dashboard.
2. Create tender.
3. Enter tender information.
4. Upload tender requirement document.
5. Define structured requirements.
6. View bidders.
7. Review bidder submissions.
8. Start verification.
9. Watch processing pipeline.
10. View compliance score.
11. View risk level.
12. View missing documents.
13. View inconsistencies.
14. View evidence.
15. View AI explanation.
16. View verification results.
17. View audit trail.
18. Make final decision.

==================================================
10. TENDER CREATION
==================================================

Create a traditional form.

Fields:

Tender ID
Tender Name
Tender Description
Organization
Department
Tender Start Date
Tender End Date
Experience Required (years)
Minimum Turnover
Minimum Bidder Age
Tender Requirement Document
Additional Requirements

Example:

Tender ID:
CPCL-2026-001

Tender Name:
Industrial Equipment Procurement

Description:
Procurement of industrial equipment.

Experience Required:
5 years

Minimum Turnover:
10000000

Required Documents:

PAN
GST
Udyam
Company Registration
Experience Certificate
Financial Statement

The officer can upload the tender requirement PDF.

==================================================
11. TENDER REQUIREMENT DOCUMENT PROCESSING
==================================================

When a tender requirement document is uploaded:

Show an animated processing pipeline.

Example:

Document Uploaded
        ↓
Reading Tender Document
        ↓
Extracting Text
        ↓
Detecting Requirements
        ↓
Structuring Requirements
        ↓
Creating Embeddings
        ↓
Indexing Tender Requirements
        ↓
Tender Ready

Use:

PyMuPDF
+
LangChain
+
Embeddings
+
pgvector

The extracted requirements should be converted into structured objects.

Example:

{
  "requirement_type": "experience",
  "description": "Bidder must have minimum 5 years experience",
  "minimum_value": 5,
  "unit": "years",
  "mandatory": true,
  "evidence_required": true
}

==================================================
12. DOCUMENT MASTER
==================================================

Do NOT hard-code document logic everywhere.

Create a document master/configuration.

Example:

PAN:

required_fields:
    pan_number
    name
    date_of_birth_or_incorporation

GST:

required_fields:
    gstin
    legal_name
    address
    registration_date

UDYAM:

required_fields:
    udyam_number
    enterprise_name
    address

COMPANY_REGISTRATION:

required_fields:
    company_name
    registration_number
    incorporation_date

EXPERIENCE_CERTIFICATE:

required_fields:
    organization
    experience_years
    project_description
    issue_date

FINANCIAL_STATEMENT:

required_fields:
    financial_year
    turnover
    auditor_name

This makes the system extensible.

==================================================
13. BIDDER CREATION
==================================================

Create bidder form.

Fields:

Bidder ID
Bidder Name
Company Details
PAN
GSTIN
Udyam Number
Experience Years
Address
Contact Details
Documents

Example:

Bidder ID:
BID-001

Bidder Name:
ABC Engineering Pvt Ltd

Experience:
8 years

Then allow multiple documents to be uploaded.

==================================================
14. DOCUMENT UPLOAD UI
==================================================

Create a modern drag-and-drop uploader.

Accepted:

PDF
PNG
JPG
JPEG

For every file display:

Filename
File size
Upload progress
Upload status

Successful:

GREEN

Failed:

RED

Processing:

BLUE/ANIMATED

Do not confuse upload success with verification success.

Use separate statuses:

UPLOADED
PROCESSING
EXTRACTED
VALIDATED
VERIFIED
FAILED
REVIEW_REQUIRED

==================================================
15. DOCUMENT CLASSIFICATION
==================================================

The system should automatically identify uploaded documents.

Example:

Uploaded file:

document_01.pdf

System detects:

PAN DOCUMENT

Another:

gst_certificate.pdf

System detects:

GST DOCUMENT

Another:

udyam.pdf

System detects:

UDYAM DOCUMENT

Classification can use:

Filename
OCR text
Regex
Document keywords
LLM fallback

Use deterministic classification first.

==================================================
16. DOCUMENT PROCESSING PIPELINE
==================================================

For every bidder document:

Step 1:

Upload

Step 2:

File validation

Step 3:

PDF/image processing

Step 4:

OCR

Step 5:

Text extraction

Step 6:

Document classification

Step 7:

Structured field extraction

Step 8:

Field validation

Step 9:

Cross-document comparison

Step 10:

Tender requirement matching

Step 11:

External/mock verification

Step 12:

Risk assessment

Step 13:

AI analysis

Step 14:

Compliance report

==================================================
17. EXTRACTION
==================================================

Extract structured fields.

Example PAN:

{
    "document_type": "PAN",
    "pan": "ABCPV1234D",
    "name": "ABC ENGINEERING PRIVATE LIMITED",
    "dob_or_incorporation": "2010-05-12"
}

GST:

{
    "document_type": "GST",
    "gstin": "27ABCDE1234F1Z5",
    "legal_name": "ABC ENGINEERING PRIVATE LIMITED",
    "trade_name": "ABC ENGINEERING",
    "address": "...",
    "registration_date": "2017-07-01"
}

Udyam:

{
    "document_type": "UDYAM",
    "udyam_number": "UDYAM-MH-26-1234567",
    "enterprise_name": "ABC ENGINEERING PRIVATE LIMITED",
    "address": "..."
}

==================================================
18. EXTRACTION VS VALIDATION VS VERIFICATION
==================================================

IMPORTANT CONCEPT.

Do not mix these concepts.

A. EXTRACTION

Question:

"What information exists in the document?"

Example:

PAN extracted:

ABCPV1234D

B. VALIDATION

Question:

"Does the extracted information follow expected rules?"

Example:

PAN format:

ABCPV1234D

Format valid = YES

C. VERIFICATION

Question:

"Can an authoritative source confirm this information?"

Example:

PAN -> external verification provider

Status:

VERIFIED

For hackathon:

Mock verification provider.

==================================================
19. FIELD VALIDATION
==================================================

Implement deterministic validation.

Examples:

PAN regex:

^[A-Z]{5}[0-9]{4}[A-Z]{1}$

GSTIN validation.

Udyam format validation.

Date validation.

Required field validation.

Numeric validation.

Experience validation.

Turnover validation.

Do NOT use the LLM for simple regex/format checks.

==================================================
20. MANDATORY DOCUMENT CHECK
==================================================

Tender defines:

PAN mandatory
GST mandatory
Udyam mandatory
Experience Certificate mandatory
Financial Statement mandatory

Bidder submits:

PAN
GST
Experience Certificate

System:

PAN -> PRESENT
GST -> PRESENT
Udyam -> MISSING
Experience Certificate -> PRESENT
Financial Statement -> MISSING

Generate:

RED FLAGS:

Missing mandatory Udyam document
Missing mandatory Financial Statement

==================================================
21. TENDER REQUIREMENT ENGINE
==================================================

Create a rule-based compliance engine.

Example:

Requirement:

Experience >= 5 years

Bidder:

Experience = 8 years

Result:

PASS

Another:

Experience >= 5 years

Bidder:

Experience = 3 years

Result:

FAIL

Another:

Requirement:

Minimum turnover >= ₹1 crore

Bidder:

₹1.5 crore

Result:

PASS

Rules must be deterministic.

==================================================
22. CROSS-DOCUMENT COMPARISON
==================================================

This is one of the most important features.

Compare information across documents.

Examples:

PAN name
GST legal name
Udyam enterprise name
Company registration name

Normalize names before comparison.

Example:

ABC ENGINEERING PRIVATE LIMITED

ABC ENGINEERING PVT LTD

ABC Engineering Pvt. Ltd.

These should not automatically be considered different.

Create normalization:

uppercase
remove punctuation
normalize PRIVATE LIMITED / PVT LTD
remove extra spaces
normalize common abbreviations

Compare:

PAN vs GST
PAN vs Udyam
GST vs Udyam
Company registration vs GST
Company registration vs PAN

Also compare:

Addresses
Registration dates
Company identifiers
Authorized person names where available

If discrepancy exists:

DO NOT say "FRAUD".

Instead:

"Potential discrepancy detected. Manual review recommended."

==================================================
23. EXTERNAL VERIFICATION ARCHITECTURE
==================================================

Create:

VerificationProvider interface.

Example:

class VerificationProvider:

    verify_pan(...)
    verify_gst(...)
    verify_udyam(...)
    verify_company(...)

Create:

MockVerificationProvider

This returns deterministic demo data.

Example:

PAN:

{
    "status": "SUCCESS",
    "source": "DEMO_VERIFICATION",
    "verified": true,
    "reference_id": "DEMO-12345"
}

Udyam:

{
    "status": "SUCCESS",
    "udyam": "UDYAM-MH-26-1234567"
}

==================================================
24. CASHFREE OPTIONAL INTEGRATION
==================================================

Create an optional Cashfree provider.

Do not make it required for MVP.

Use environment variables:

CASHFREE_CLIENT_ID
CASHFREE_CLIENT_SECRET
CASHFREE_ENV=sandbox

Example endpoint for PAN-to-Udyam sandbox integration:

POST:

https://sandbox.cashfree.com/verification/pan-udyam

The integration must be isolated inside:

integrations/cashfree_provider.py

Never expose secrets in frontend.

If credentials are unavailable:

automatically fall back to MockVerificationProvider.

The UI must indicate:

Mock verification used

instead of pretending the result came from a government API.

==================================================
25. RAG SYSTEM
==================================================

Use RAG where it actually provides value.

Do NOT use RAG for simple regex checks.

RAG should primarily answer:

"What does the tender require?"

and:

"What evidence in the bidder documents supports this requirement?"

Pipeline:

Tender PDF
   ↓
PyMuPDF
   ↓
Text
   ↓
Chunking
   ↓
Embeddings
   ↓
pgvector
   ↓
Retriever
   ↓
Relevant tender requirement

Bidder documents:

PDF
   ↓
OCR
   ↓
Text
   ↓
Chunking
   ↓
Embeddings
   ↓
pgvector
   ↓
Relevant evidence

Then compare requirement and evidence.

==================================================
26. LLM ROLE
==================================================

The local LLM is NOT the source of truth.

Use LLM for:

- Understanding natural-language tender requirements
- Explaining discrepancies
- Summarizing evidence
- Contextual document comparison
- Identifying potentially relevant information
- Generating human-readable recommendations
- Generating explanations for risk flags

Do NOT use LLM for:

- PAN regex
- GST format
- Required document existence
- Mathematical score calculation
- Final qualification
- Final disqualification

==================================================
27. STRUCTURED LLM OUTPUT
==================================================

Force the LLM to return JSON.

Example:

{
    "summary": "...",
    "findings": [
        {
            "type": "MISSING_DOCUMENT",
            "severity": "HIGH",
            "description": "...",
            "evidence": "..."
        }
    ],
    "recommendations": [
        "Request missing financial statement"
    ],
    "manual_review_required": true
}

Validate LLM output with Pydantic.

If parsing fails:

retry once.

If still fails:

use fallback report.

==================================================
28. LANGGRAPH WORKFLOW
==================================================

Create a LangGraph state.

Example:

class VerificationState:

    tender_id
    bidder_id
    documents
    extracted_data
    validations
    requirements
    matched_evidence
    cross_document_results
    external_verifications
    risk_results
    llm_analysis
    final_report

Nodes:

load_tender
load_bidder
classify_documents
extract_text
extract_fields
validate_fields
check_requirements
retrieve_evidence
cross_document_check
external_verification
calculate_risk
llm_analysis
generate_report
save_audit_log

The workflow must be resumable and easy to debug.

==================================================
29. RISK ENGINE
==================================================

Risk calculation must be deterministic.

Example configurable weights:

Missing mandatory document:
+30

Critical field missing:
+20

Invalid format:
+15

Cross-document discrepancy:
+15

External verification failure:
+30

Authenticity warning:
+20

Experience requirement failure:
+30

Turnover requirement failure:
+30

Clamp risk between 0 and 100.

Compliance score:

100 - risk_points

Example:

Risk = 12

Compliance score = 88

Risk levels:

90-100:
LOW

70-89:
MEDIUM

0-69:
HIGH

Make thresholds configurable.

IMPORTANT:

These numbers are demo scoring rules.

They are NOT official government rules.

==================================================
30. AUTHENTICITY SIGNALS
==================================================

Optionally detect document quality signals.

Examples:

- Blurry document
- Very low resolution
- Suspicious image manipulation indicators
- Missing expected sections
- Inconsistent fonts
- Overwriting indicators

These are ONLY risk signals.

Never claim:

"This document is fraudulent."

Instead say:

"Document authenticity warning detected. Manual verification recommended."

==================================================
31. DUPLICATE / CROSS-BID DETECTION
==================================================

Implement an optional feature.

Compare multiple bidders.

Potential duplicate signals:

Same PAN
Same GSTIN
Same address
Same phone number
Same email
Same document hash
Same company identifier

Example:

Bidder A:
Address = X

Bidder B:
Address = X

Show:

"Potential shared information detected."

Do not claim collusion or fraud.

==================================================
32. MULTIPLE BIDDERS
==================================================

This is critical.

A tender can have:

Bidder A
Bidder B
Bidder C
Bidder D

The dashboard should compare them.

Example:

Bidder         Score      Risk       Review
ABC Ltd        96         Low        Ready
XYZ Ltd        91         Low        Ready
PQR Ltd        78         Medium     Review
LMN Ltd        62         High       Review

Do NOT call this automatic award ranking.

Call it:

Compliance / Risk Prioritization

The officer still makes the final procurement decision.

==================================================
33. MAIN DASHBOARD
==================================================

Create a professional government-enterprise style dashboard.

Sections:

Top KPI cards:

Total Tenders
Active Tenders
Total Bidders
Pending Reviews

Tender table:

Tender ID
Tender Name
Bidders
Status
Created Date
Action

Bidder compliance table:

Bidder
Compliance Score
Risk Level
Documents
Missing Requirements
Verification Status
Action

Use badges:

LOW
MEDIUM
HIGH

Use animations but keep the interface professional.

==================================================
34. TENDER DETAIL PAGE
==================================================

Show:

Tender information

Requirements

Uploaded tender document

Number of bidders

Overall statistics

Example:

Requirements:
8

Bidders:
12

Low Risk:
7

Medium Risk:
3

High Risk:
2

Then bidder table.

==================================================
35. BIDDER DETAIL PAGE
==================================================

Show:

Bidder name
Bidder ID
Company details
Experience
Compliance score
Risk level
Verification status

Then:

DOCUMENTS

PAN
GST
UDYAM
Company Registration
Experience Certificate
Financial Statement

Each document:

Status
Extracted fields
Validation
Verification
Issues

==================================================
36. PROCESSING SCREEN
==================================================

This should be visually impressive for the hackathon.

Show:

┌─────────────────────────────────┐
│      AI VERIFICATION ENGINE     │
└─────────────────────────────────┘

✓ Documents uploaded

✓ Document classification

✓ OCR extraction

✓ PAN detected

✓ GST detected

✓ Udyam detected

✓ Data extraction

✓ Field validation

✓ Tender requirement matching

✓ Cross-document analysis

⟳ AI contextual analysis

○ Compliance report

Animate the current step.

Do NOT make fake delays unnecessarily long.

Use actual backend job state if possible.

==================================================
37. COMPLIANCE REPORT
==================================================

Create a detailed report.

Header:

Bidder:
ABC Engineering Pvt Ltd

Tender:
CPCL-2026-001

Compliance Score:
92%

Risk:
LOW

Verification:

8 / 8 documents processed

Then:

REQUIREMENT STATUS

Requirement | Status | Evidence | Remarks

PAN | PASS | PAN document | Valid format
GST | PASS | GST certificate | Verified
Udyam | PASS | Udyam certificate | Verified
Experience | PASS | Experience certificate | 8 years
Turnover | PASS | Financial statement | Meets requirement

Then:

RED FLAGS

None

or:

Potential discrepancy in registered address.

Then:

AI SUMMARY

The bidder appears to satisfy the configured tender requirements based on submitted documents and available verification evidence.

Then:

RECOMMENDATION

Proceed to Procurement Officer review.

IMPORTANT:

Never say:

"Bidder is automatically qualified."

Instead:

"Recommended for Procurement Officer review."

==================================================
38. AUDIT TRAIL
==================================================

Every verification action must be logged.

Example:

2026-09-10 10:31
Tender created

2026-09-10 10:35
Tender requirement uploaded

2026-09-10 10:36
Tender requirements extracted

2026-09-10 10:40
Bidder ABC submitted documents

2026-09-10 10:41
PAN extracted

2026-09-10 10:41
GST extracted

2026-09-10 10:42
Cross-document validation completed

2026-09-10 10:43
Mock verification completed

2026-09-10 10:44
Compliance report generated

2026-09-10 10:50
Procurement Officer reviewed result

Store:

timestamp
user
action
entity
result
details

==================================================
39. DATABASE DESIGN
==================================================

Create SQLAlchemy models.

TABLE:

users

id
name
email
role
created_at

tenders

id
tender_id
name
description
organization
department
experience_required
minimum_turnover
status
created_at

tender_requirements

id
tender_id
requirement_type
name
description
mandatory
minimum_value
maximum_value
unit
evidence_required
created_at

bidders

id
bidder_id
name
details
experience_years
address
created_at

bids

id
tender_id
bidder_id
status
submitted_at

documents

id
bid_id
document_type
filename
file_path
mime_type
file_size
status
created_at

extracted_data

id
document_id
field_name
field_value
confidence
source_page
created_at

validation_results

id
document_id
field
status
message
severity
created_at

verification_results

id
document_id
provider
status
reference_id
response_json
verified_at

cross_document_checks

id
bid_id
field
documents_compared
status
details
severity

risk_assessments

id
bid_id
risk_score
compliance_score
risk_level
created_at

red_flags

id
bid_id
type
severity
description
evidence
status
created_at

ai_reports

id
bid_id
summary
recommendation
json_result
model
created_at

audit_logs

id
user_id
entity_type
entity_id
action
details
timestamp

==================================================
40. API ENDPOINTS
==================================================

Implement REST API.

HEALTH:

GET /api/health

TENDERS:

POST /api/tenders
GET /api/tenders
GET /api/tenders/{id}
PUT /api/tenders/{id}
DELETE /api/tenders/{id}

TENDER REQUIREMENTS:

POST /api/tenders/{id}/requirements
GET /api/tenders/{id}/requirements

TENDER DOCUMENT:

POST /api/tenders/{id}/requirement-document
POST /api/tenders/{id}/process

BIDDERS:

POST /api/bidders
GET /api/bidders
GET /api/bidders/{id}

BIDS:

POST /api/tenders/{tender_id}/bids
GET /api/tenders/{tender_id}/bids
GET /api/bids/{id}

DOCUMENTS:

POST /api/bids/{bid_id}/documents
GET /api/bids/{bid_id}/documents
GET /api/documents/{id}

PROCESSING:

POST /api/documents/{id}/process

EXTRACTION:

GET /api/documents/{id}/extracted-data

VALIDATION:

POST /api/bids/{id}/validate

VERIFICATION:

POST /api/bids/{id}/verify

ANALYSIS:

POST /api/bids/{id}/analyze

REPORT:

GET /api/bids/{id}/report

AUDIT:

GET /api/bids/{id}/audit-log

==================================================
41. API RESPONSE FORMAT
==================================================

Use consistent response structures.

Success:

{
    "success": true,
    "data": {},
    "message": "..."
}

Error:

{
    "success": false,
    "error": {
        "code": "...",
        "message": "..."
    }
}

Use HTTP status codes correctly.

==================================================
42. FRONTEND ROUTES
==================================================

Create:

/

Dashboard

/tenders

Tender list

/tenders/new

Create tender

/tenders/:id

Tender details

/tenders/:id/bidders

Bidder list

/tenders/:id/bidders/new

Add bidder

/bids/:id

Bid detail

/bids/:id/processing

Processing page

/bids/:id/report

Compliance report

/audit/:bidId

Audit trail

==================================================
43. FRONTEND COMPONENTS
==================================================

Create reusable components:

Navbar
Sidebar
PageHeader
StatCard
DataTable
StatusBadge
RiskBadge
ComplianceScore
FileUploader
DocumentCard
DocumentStatus
ProcessingPipeline
RequirementCard
RequirementStatus
RedFlagCard
VerificationCard
EvidenceCard
ComplianceChart
RiskChart
ComparisonTable
AuditTimeline
AIRecommendation
EmptyState
LoadingState
ErrorState
ConfirmDialog

==================================================
44. UI DESIGN
==================================================

Style:

Professional
Government enterprise
Modern
Clean
Trustworthy

Use:

White/light background
Neutral enterprise colors
Clear status colors
Good spacing
Accessible contrast

Do not make it look like a gaming dashboard.

Use Framer Motion for:

Page transitions
Processing animation
Card entrance
Progress updates
Status changes

==================================================
45. IMPORTANT STATUS DISTINCTION
==================================================

Do NOT show only:

"Verified"

because there are multiple stages.

Use:

Upload Status
Extraction Status
Validation Status
Verification Status
Compliance Status

Example:

Upload:
SUCCESS

Extraction:
SUCCESS

Validation:
PASS

Verification:
VERIFIED

Tender Compliance:
PASS

==================================================
46. COMPLIANCE LOGIC
==================================================

For every tender:

Load requirements.

For every bidder:

Check:

1. Required document exists.
2. Required fields exist.
3. Field formats are valid.
4. Numeric requirements are satisfied.
5. Experience requirement is satisfied.
6. Turnover requirement is satisfied.
7. Cross-document data is consistent.
8. External/mock verification result.
9. Other tender-specific rules.

Generate:

PASS
FAIL
REVIEW

Use REVIEW when:

- evidence is ambiguous
- discrepancy exists
- external verification unavailable
- LLM cannot confidently interpret a requirement

==================================================
47. EVIDENCE-FIRST DESIGN
==================================================

Every important compliance result should show evidence.

Example:

Requirement:

"Minimum 5 years experience"

Result:

PASS

Evidence:

Experience Certificate

Extracted:

8 years

Source:

Page 2

This is extremely important for explainability.

Never produce unexplained AI scores.

==================================================
48. AI EXPLANATION
==================================================

For each red flag:

Show:

Issue
Severity
Evidence
Reason
Recommendation

Example:

Potential Address Discrepancy

Severity:
MEDIUM

Evidence:

PAN:
Mumbai

GST:
Pune

Recommendation:

"Review the registered address and supporting documents before final decision."

==================================================
49. SEARCH / FILTER
==================================================

Dashboard must allow filtering bidders by:

Risk
Compliance Score
Verification Status
Missing Documents
Tender

Search by:

Bidder name
Bidder ID
Tender ID

==================================================
50. REPORT EXPORT
==================================================

For MVP implement:

Print-friendly compliance report.

Optionally generate PDF.

Report should include:

Tender information
Bidder information
Requirement matrix
Documents
Validation results
Verification results
Red flags
Risk score
Compliance score
AI recommendation
Audit information

Include:

"Final decision to be made by Procurement Officer."

==================================================
51. SECURITY
==================================================

Implement basic security.

Never expose:

DATABASE_URL
LLM credentials
Cashfree credentials
Secrets

to frontend.

Use:

.env

and:

.env.example

Add:

.env

to .gitignore.

Validate uploaded files.

Allowed:

PDF
PNG
JPG
JPEG

Set file size limit.

Prevent:

Path traversal
Unsafe filenames
Executable uploads

Generate safe filenames.

==================================================
52. ENVIRONMENT VARIABLES
==================================================

Create:

.env.example

Example:

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bid_compliance

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=

LLM_PROVIDER=ollama

VERIFICATION_PROVIDER=mock

CASHFREE_CLIENT_ID=
CASHFREE_CLIENT_SECRET=
CASHFREE_ENV=sandbox

UPLOAD_DIR=./uploads

MAX_UPLOAD_SIZE_MB=20

APP_ENV=development

==================================================
53. LOCAL DEVELOPMENT
==================================================

The complete application must run using:

docker compose up

Services:

frontend
backend
postgres

Ollama can remain installed locally because it may require GPU/native runtime.

Do not put Ollama inside the default Docker Compose unless there is a clear reason.

Local architecture:

Browser
   |
Frontend
   |
Backend
   |
PostgreSQL

Backend
   |
Ollama localhost

Backend
   |
Mock Verification

==================================================
54. DOCKER
==================================================

Create backend Dockerfile.

Requirements:

Python slim image
Install dependencies
Copy source
Run FastAPI with Uvicorn

Example command:

uvicorn app.main:app --host 0.0.0.0 --port 8000

Create frontend Dockerfile.

Use:

Node build stage

then:

Nginx production stage.

Expose:

Frontend 80

Backend 8000

==================================================
55. DOCKER COMPOSE
==================================================

Create:

docker-compose.yml

Services:

postgres
backend
frontend

PostgreSQL:

database:
bid_compliance

user:
postgres

password:
postgres

Backend must connect using:

postgres service hostname

not localhost.

Use health checks.

Backend should wait for PostgreSQL to become healthy.

==================================================
56. DATABASE MIGRATIONS
==================================================

Use Alembic.

Commands:

alembic revision --autogenerate
alembic upgrade head

Do not manually create production tables from application startup.

==================================================
57. SEED DATA
==================================================

Create a seed script.

Example:

3 tenders

5 bidders

multiple documents

different compliance outcomes.

Create realistic fictional data.

Do NOT use real personal data.

Example:

ABC Engineering Pvt Ltd
XYZ Industrial Systems
PQR Technologies
LMN Manufacturing

Create:

LOW risk bidder
MEDIUM risk bidder
HIGH risk bidder

Examples:

Bidder A:

96%
LOW

Bidder B:

82%
MEDIUM

Bidder C:

61%
HIGH

This makes the dashboard impressive during demonstration.

==================================================
58. DEMO DATA
==================================================

Include fake documents or generated demo text/PDFs.

Examples:

PAN
GST
Udyam
Experience Certificate
Financial Statement

Documents should contain clearly fictional/demo data.

Never use real people's PAN numbers.

==================================================
59. MOCK VERIFICATION
==================================================

Create deterministic mock verification.

Example:

Demo PAN:

ABCPV1234D

returns:

SUCCESS

Demo GST:

27ABCDE1234F1Z5

returns:

SUCCESS

Demo Udyam:

UDYAM-MH-26-1234567

returns:

SUCCESS

Invalid demo identifier:

returns:

FAILED

This allows the entire workflow to be demonstrated offline.

==================================================
60. TESTING
==================================================

Use pytest.

Create unit tests for:

PAN validation
GST validation
Udyam validation
Name normalization
Document classification
Requirement engine
Risk engine
Compliance score
Cross-document comparison
Mock verification
API health
Tender creation
Bidder creation

Example test:

experience_required = 5
bidder_experience = 8

Expected:

PASS

Example:

experience_required = 5
bidder_experience = 3

Expected:

FAIL

==================================================
61. FRONTEND TESTING
==================================================

Use Vitest.

Test:

Components
Forms
Status badges
Compliance calculations displayed
API error handling

==================================================
62. CI PIPELINE
==================================================

Create:

.github/workflows/ci.yml

Pipeline should run on:

push
pull_request

Stages:

1. Backend lint
2. Backend tests
3. Frontend lint
4. Frontend tests
5. Frontend build
6. Docker build

Use:

ruff

pytest

eslint

vitest

npm run build

docker build

The CI pipeline must fail if any important test/build fails.

==================================================
63. GITHUB ACTIONS
==================================================

Example conceptual workflow:

checkout

setup Python

install backend requirements

run ruff

run pytest

setup Node

npm install

run ESLint

run Vitest

run npm build

build backend Docker image

build frontend Docker image

Do not require production secrets in CI for basic tests.

Use mocked integrations.

==================================================
64. RAILWAY DEPLOYMENT
==================================================

Deploy backend to Railway.

Deploy PostgreSQL on Railway.

Frontend can be:

Railway or Vercel.

Prefer Railway if keeping the architecture simple.

Production architecture:

Internet
   |
Frontend
   |
Railway Backend
   |
Railway PostgreSQL

IMPORTANT:

Do not assume local Ollama will work on Railway.

Railway backend cannot use:

http://localhost:11434

to reach the developer's Mac.

Therefore:

Development:

LLM_PROVIDER=ollama

Production hackathon demo:

LLM_PROVIDER=mock

OR use a separately deployed inference service.

==================================================
65. RAILWAY ENVIRONMENT
==================================================

Configure:

DATABASE_URL

LLM_PROVIDER

OLLAMA_BASE_URL

OLLAMA_MODEL

VERIFICATION_PROVIDER

CASHFREE_CLIENT_ID

CASHFREE_CLIENT_SECRET

CASHFREE_ENV

UPLOAD_DIR

MAX_UPLOAD_SIZE_MB

Do not commit secrets.

==================================================
66. RAILWAY HEALTH CHECK
==================================================

Implement:

GET /api/health

Response:

{
    "success": true,
    "status": "healthy",
    "database": "connected"
}

Configure Railway health check to use:

/api/health

==================================================
67. RAILWAY STORAGE WARNING
==================================================

Local filesystem storage on Railway should NOT be treated as permanent storage.

For MVP:

local filesystem can be used temporarily.

But design:

StorageProvider

with:

LocalStorageProvider

and future:

S3StorageProvider

This allows migration later.

For the hackathon demo, local temporary storage is acceptable if clearly understood.

==================================================
68. LOGGING
==================================================

Implement structured logging.

Log:

request
response status
document processing
verification provider
errors
workflow steps

Never log:

PAN unnecessarily
passwords
API secrets
Cashfree credentials

==================================================
69. ERROR HANDLING
==================================================

Handle:

Invalid PDF
Corrupt file
OCR failure
LLM unavailable
Database unavailable
Verification provider unavailable
Invalid extracted data
Missing requirements
Malformed LLM response

The application must not crash because Ollama is unavailable.

If LLM fails:

fall back to deterministic report.

If verification API fails:

mark:

VERIFICATION_UNAVAILABLE

and continue.

==================================================
70. OFFLINE-FIRST DEMO
==================================================

This is VERY IMPORTANT for the hackathon.

The complete MVP must work without:

Internet
Government APIs
Cashfree credentials
Ollama

Fallback chain:

LLM:

Ollama
   ↓
Mock LLM

Verification:

Cashfree
   ↓
Mock Verification

Embeddings:

Local embedding model
   ↓
Fallback basic retrieval if unavailable

The demo must never become unusable because an external service is unavailable.

==================================================
71. OBSERVABILITY
==================================================

Create a processing job/status system.

For every bid verification:

job_id

status:

QUEUED
PROCESSING
COMPLETED
FAILED

progress:

0-100

current_step

The frontend polls:

GET /api/bids/{id}/processing-status

or uses WebSocket if simple to implement.

Polling is acceptable for MVP.

==================================================
72. PROCESSING STATUS EXAMPLE
==================================================

Return:

{
    "status": "PROCESSING",
    "progress": 68,
    "current_step": "Cross-document analysis",
    "steps": [
        {
            "name": "Document Upload",
            "status": "COMPLETED"
        },
        {
            "name": "OCR",
            "status": "COMPLETED"
        },
        {
            "name": "Data Extraction",
            "status": "COMPLETED"
        },
        {
            "name": "Requirement Matching",
            "status": "COMPLETED"
        },
        {
            "name": "Cross-document Analysis",
            "status": "PROCESSING"
        },
        {
            "name": "AI Analysis",
            "status": "PENDING"
        }
    ]
}

==================================================
73. ASYNCHRONOUS PROCESSING
==================================================

For MVP do not introduce unnecessary infrastructure such as Kafka or Celery unless absolutely required.

Use FastAPI background tasks or a simple job runner.

The architecture should allow Celery/Redis later.

Keep the MVP simple.

==================================================
74. API DOCUMENTATION
==================================================

FastAPI automatically provides:

/docs

and:

/redoc

Ensure all API endpoints have:

Descriptions
Request schemas
Response schemas
Examples

==================================================
75. README
==================================================

Create a professional README.

Include:

Project name

Problem

Solution

Features

Architecture

Tech stack

Folder structure

Local setup

Docker setup

Environment variables

Ollama setup

Mock verification

API documentation

Testing

CI/CD

Railway deployment

Demo workflow

Future government integrations

Security

Limitations

==================================================
76. README ARCHITECTURE DIAGRAM
==================================================

Include Mermaid diagrams.

Example:

```mermaid
flowchart TD

A[Procurement Officer] --> B[React Frontend]

B --> C[FastAPI Backend]

C --> D[Document Processing]

D --> E[OCR]

E --> F[Structured Extraction]

F --> G[Compliance Engine]

G --> H[RAG]

G --> I[Rule Engine]

G --> J[Risk Engine]

G --> K[Verification Providers]

H --> L[Local LLM]

K --> M[Mock Verification]

K --> N[Future Government APIs]

G --> O[Compliance Report]

O --> A