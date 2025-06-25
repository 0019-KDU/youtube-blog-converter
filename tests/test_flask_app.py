from unittest.mock import patch, MagicMock
import pytest
import uuid
from app import app as flask_app
import io

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem for tests
    flask_app.config['SESSION_FILE_DIR'] = './test_flask_session/'
    with flask_app.test_client() as client:
        with client.session_transaction() as session:
            session.clear()
        yield client

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"YouTube to Blog Converter" in response.data

def test_successful_generation(client):
    # Mock the blog generation function
    with patch('app.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://youtube.com/test',
            'language': 'en'
        })
        
        # Verify redirect to results page
        assert response.status_code == 302
        assert response.location.endswith('/results')
        
        # Check that session has content_id
        with client.session_transaction() as session:
            assert 'content_id' in session
            content_id = session['content_id']
            assert content_id in session
            assert session[content_id]['blog_content'] == "Generated blog content"

def test_results_page(client):
    # Create test content ID
    content_id = str(uuid.uuid4())
    
    with client.session_transaction() as session:
        session['content_id'] = content_id
        session[content_id] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }
    
    response = client.get('/results')
    assert response.status_code == 200
    assert b"Test content" in response.data

@patch('app.send_file')
@patch('app.PDFTool')
def test_pdf_download(mock_pdf_tool, mock_send_file, client):
    # Create test content ID
    content_id = str(uuid.uuid4())
    
    # Mock PDF generation
    mock_pdf_instance = MagicMock()
    mock_pdf_instance.generate_pdf_bytes.return_value = b'PDF content'
    mock_pdf_tool.return_value = mock_pdf_instance
    
    # Configure send_file mock
    mock_send_file.return_value = MagicMock(status_code=200)

    # Set session data
    with client.session_transaction() as session:
        session['content_id'] = content_id
        session[content_id] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://youtube.com/test'
        }

    # Make request
    response = client.get('/download')

    # Verify response and mock calls
    assert response.status_code == 200
    mock_send_file.assert_called_once()
    mock_pdf_tool.assert_called_once()
    mock_pdf_instance.generate_pdf_bytes.assert_called_once_with('Test content')
    
    # Verify send_file arguments
    args, kwargs = mock_send_file.call_args
    assert isinstance(args[0], io.BytesIO)
    assert kwargs['as_attachment'] is True
    assert kwargs['download_name'] == 'blog_article.pdf'
    assert kwargs['mimetype'] == 'application/pdf'
    
    # Verify session was cleared
    with client.session_transaction() as session:
        assert content_id not in session
        assert 'content_id' not in session

def test_invalid_url_handling(client):
    response = client.post('/generate', data={'youtube_url': ''})
    assert response.status_code == 200
    assert b"YouTube URL is required" in response.data

def test_error_handling(client):
    with patch('app.generate_blog_from_youtube') as mock_generate:
        mock_generate.side_effect = RuntimeError("Test error")
        
        response = client.post('/generate', data={
            'youtube_url': 'https://youtube.com/test',
            'language': 'en'
        })
        
        assert response.status_code == 200
        assert b"Error: Test error" in response.data

def test_missing_session_redirects(client):
    # Test results without session
    response = client.get('/results')
    assert response.status_code == 302
    assert response.location.endswith('/')
    
    # Test download without session
    response = client.get('/download')
    assert response.status_code == 302
    assert response.location.endswith('/')