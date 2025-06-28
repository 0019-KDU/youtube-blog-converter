import pytest
import uuid
from app import app as flask_app
import io
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SESSION_TYPE'] = 'filesystem'
    flask_app.config['SESSION_FILE_DIR'] = './test_flask_session/'
    
    with flask_app.test_client() as client:
        with client.session_transaction() as sess:
            sess.clear()
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"YouTube to Blog Converter" in response.data

@patch('app.generate_blog_from_youtube')
def test_successful_generation(mock_generate, client):
    mock_generate.return_value = "Generated blog content"
    response = client.post('/generate', data={'youtube_url': 'https://youtube.com/test'})
    assert response.status_code == 302
    assert response.location.endswith('/results')

def test_results_page(client):
    content_id = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess['content_id'] = content_id
        sess[content_id] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }
    
    response = client.get('/results')
    assert response.status_code == 200
    assert b"Test content" in response.data

@patch('app.PDFTool')
def test_pdf_download(mock_pdf_tool, client):
    content_id = str(uuid.uuid4())
    mock_pdf_instance = MagicMock()
    mock_pdf_instance.generate_pdf_bytes.return_value = b'PDF content'
    mock_pdf_tool.return_value = mock_pdf_instance

    with client.session_transaction() as sess:
        sess['content_id'] = content_id
        sess[content_id] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }

    response = client.get('/download')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.headers['Content-Disposition'] == 'attachment; filename=blog_article.pdf'
    assert response.data == b'PDF content'

def test_invalid_url_handling(client):
    response = client.post('/generate', data={'youtube_url': ''})
    assert response.status_code == 200
    assert b"YouTube URL is required" in response.data

@patch('app.generate_blog_from_youtube')
def test_error_handling(mock_generate, client):
    mock_generate.side_effect = RuntimeError("Test error")
    response = client.post('/generate', data={'youtube_url': 'https://youtube.com/test'})
    assert response.status_code == 200
    assert b"Error: Test error" in response.data

def test_missing_session_redirects(client):
    response = client.get('/results')
    assert response.status_code == 302
    assert response.location.endswith('/')
    
    response = client.get('/download')
    assert response.status_code == 302
    assert response.location.endswith('/')