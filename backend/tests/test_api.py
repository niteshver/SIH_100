from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['mode'] == 'demo'

def test_report_is_human_review_only():
    report = client.get('/api/tenders/GEM%2F2026%2FB%2F4819201/report').json()
    assert report['human_review_required'] is True
    assert report['ai_can_decide'] is False

def test_rejects_automatic_decision():
    response = client.post('/api/decisions', json={'bidder_id': '1', 'decision': 'Qualified'})
    assert response.status_code == 400
