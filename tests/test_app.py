# ✅ tests/test_app.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"YouTube" in response.data or b"URL" in response.data

def test_generate_blog_without_url(client):
    response = client.post('/generate', data={'youtube_url': ''})
    assert b"YouTube URL is required" in response.data

def test_results_no_session(client):
    response = client.get('/results')
    assert response.status_code == 302  # Redirect

def test_download_pdf_no_session(client):
    response = client.get('/download')
    assert response.status_code == 302