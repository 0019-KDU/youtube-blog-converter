import pytest
from app import app
from unittest.mock import patch, MagicMock
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test_secret'
    with app.test_client() as client:
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"YouTube Video URL" in response.data

@patch('src.main.generate_blog_from_youtube')
def test_successful_generation(mock_generate, client):
    mock_generate.return_value = ("Blog content", "test.pdf")
    
    response = client.post('/generate', data={'youtube_url': 'https://youtube.com/test'})
    assert response.status_code == 302  # Redirect to results

def test_results_page(client):
    with client.session_transaction() as session:
        session['result_data'] = {
            'blog_content': 'Test content',
            'pdf_path': 'test.pdf',
            'youtube_url': 'https://youtube.com/test'
        }
    
    response = client.get('/results')
    assert response.status_code == 200
    assert b"Test content" in response.data

@patch('app.send_file')
@patch('os.path.exists', return_value=True)
def test_pdf_download(mock_exists, mock_send_file, client):
    # Mock the send_file response
    mock_send_file.return_value = MagicMock(status_code=200)
    
    # Set session data
    with client.session_transaction() as session:
        session['result_data'] = {
            'pdf_path': 'test.pdf',
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }
    
    response = client.get('/download')
    
    # Verify response
    assert response.status_code == 200
    
    # Verify send_file was called correctly
    mock_send_file.assert_called_once()
    args, kwargs = mock_send_file.call_args
    assert kwargs['as_attachment'] is True
    assert kwargs['download_name'] == 'blog_article.pdf'