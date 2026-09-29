from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['mode'] == 'connected'

def test_report_is_human_review_only():
    report = client.get('/api/tenders/demo-tender/report').json()
    assert report['human_review_required'] is True
    assert report['ai_can_decide'] is False

def test_rejects_automatic_decision():
    response = client.post('/api/decisions', json={'bidder_id': '1', 'decision': 'Qualified'})
    assert response.status_code == 400

def test_bidder_document_upload_cors_preflight():
    response = client.options(
        '/api/applications/APP-test/documents',
        headers={
            'Origin': 'https://www.chatlyme.xyz',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        },
    )
    assert response.status_code == 200
    assert response.headers.get('access-control-allow-origin') == 'https://www.chatlyme.xyz'
    assert response.headers.get('access-control-allow-credentials') == 'true'
