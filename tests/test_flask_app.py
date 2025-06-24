from unittest.mock import patch, MagicMock
import pytest
from app import app as flask_app
import io  # Import needed for PDF testing

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
    # Patch the function where it's used in the app module
    with patch('app.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://youtube.com/test',
            'language': 'en'
        })
        
        # Verify redirect to results page
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

@patch('app.send_file')  # Patch send_file where it's used in the app
@patch('app.PDFTool')    # Patch PDFTool where it's used in the app
def test_pdf_download(mock_pdf_tool, mock_send_file, client):
    # Mock PDFTool
    mock_pdf_instance = MagicMock()
    mock_pdf_instance.generate_pdf_bytes.return_value = b'PDF content'
    mock_pdf_tool.return_value = mock_pdf_instance
    
    # Configure send_file mock to return a response
    mock_send_file.return_value = MagicMock(status_code=200)

    # Set session data through test client
    with client.session_transaction() as session:
        session['result_data'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }

    # Make the request
    response = client.get('/download')

    # Verify response and mock calls
    assert response.status_code == 200
    mock_send_file.assert_called_once()
    mock_pdf_tool.assert_called_once()
    
    # Verify PDFTool was called with the correct content
    mock_pdf_instance.generate_pdf_bytes.assert_called_once_with('Test content')
    
    # Verify send_file was called with the correct arguments
    args, kwargs = mock_send_file.call_args
    assert isinstance(args[0], io.BytesIO)
    assert kwargs['as_attachment'] is True
    assert kwargs['download_name'] == 'blog_article.pdf'
    assert kwargs['mimetype'] == 'application/pdf'