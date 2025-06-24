from unittest.mock import patch, MagicMock
import pytest
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"YouTube to Blog Converter" in response.data

def test_successful_generation(client):
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://youtube.com/test',
            'language': 'en'
        })
        
        assert response.status_code == 302
        assert response.location.endswith('/results')

def test_results_page(client):
    with client.session_transaction() as session:
        session['result_data'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }
    
    response = client.get('/results')
    assert response.status_code == 200
    assert b"Test content" in response.data

@patch('app.send_file')
@patch('src.tool.PDFTool')  # Corrected patch target
def test_pdf_download(mock_pdf_tool, mock_send_file, client):
    # Mock PDFTool
    mock_pdf_instance = MagicMock()
    mock_pdf_instance.generate_pdf_bytes.return_value = b'PDF content'
    mock_pdf_tool.return_value = mock_pdf_instance
    
    # Mock send_file response
    mock_send_file.return_value = MagicMock(status_code=200)

    # Set session data
    with client.session_transaction() as session:
        session['result_data'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }

    response = client.get('/download')

    # Verify response
    assert response.status_code == 200
    mock_send_file.assert_called_once()
    mock_pdf_tool.assert_called_once()