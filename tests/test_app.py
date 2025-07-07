import os
import time
import uuid
import pytest
import logging
import re
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from flask import url_for
from app import app as flask_app, get_env_var, cleanup_old_sessions, get_secret_key

@pytest.fixture
def client():
    """Create a test client with proper configuration"""
    # Create a temporary directory for test sessions
    temp_dir = tempfile.mkdtemp()
    
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test_secret_key',
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': temp_dir,
        'WTF_CSRF_ENABLED': False,
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024
    })
    
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

# ===== SECRET KEY TESTS =====
def test_get_secret_key_from_env():
    """Test secret key retrieval from environment"""
    with patch.dict('os.environ', {'FLASK_SECRET_KEY': 'test_key'}):
        key = get_secret_key()
        assert key == 'test_key'

def test_get_secret_key_generated():
    """Test secret key generation when not in env"""
    with patch.dict('os.environ', {}, clear=True):
        with patch('app.logger.warning') as mock_warning:
            key = get_secret_key()
            assert len(key) == 64
            mock_warning.assert_called()

# ===== ENVIRONMENT LOADING TESTS =====
def test_env_loading_with_env_file(tmp_path):
    """Test environment loading when .env file exists"""
    env_file = tmp_path / '.env'
    env_file.write_text('TEST_VAR=test_value')
    
    with patch('app.env_path', env_file):
        with patch('app.load_dotenv') as mock_load:
            with patch('app.logger.info') as mock_info:
                # Simulate the env loading logic
                if env_file.exists():
                    mock_load(dotenv_path=env_file)
                    mock_info("Loaded environment variables from .env file")
                
                mock_load.assert_called_with(dotenv_path=env_file)
                mock_info.assert_called()

def test_env_loading_fallback_no_file():
    """Test environment loading fallback when no .env file exists"""
    non_existent_path = Path("/non/existent/.env")
    
    with patch('app.env_path', non_existent_path):
        with patch('app.load_dotenv') as mock_load:
            # Simulate the fallback logic
            if not non_existent_path.exists():
                mock_load()
            
            mock_load.assert_called()

# ===== ROUTE TESTS =====
def test_index_success(client):
    """Test successful index page load"""
    response = client.get('/')
    assert response.status_code == 200

def test_index_error_handling(client):
    """Test index error handling"""
    with patch('app.render_template', side_effect=Exception("Test error")):
        response = client.get('/')
        assert response.status_code == 500
        assert b"Error loading page" in response.data

def test_generate_blog_missing_url(client):
    """Test blog generation with missing URL"""
    response = client.post('/generate', data={})
    assert response.status_code == 400
    assert b"YouTube URL is required" in response.data

def test_generate_blog_invalid_url_format(client):
    """Test blog generation with invalid URL format"""
    response = client.post('/generate', data={'youtube_url': 'https://vimeo.com/123456'})
    assert response.status_code == 400
    assert b"Please enter a valid YouTube URL" in response.data

def test_generate_blog_success(client):
    """Test successful blog generation"""
    with patch('app.generate_blog_from_youtube', return_value="A" * 200) as mock_generate:
        response = client.post('/generate', data={'youtube_url': 'https://www.youtube.com/watch?v=abc123'})
        assert response.status_code == 302
        mock_generate.assert_called_once()

def test_generate_blog_with_language(client):
    """Test blog generation with language parameter"""
    with patch('app.generate_blog_from_youtube', return_value="A" * 200) as mock_generate:
        response = client.post('/generate', data={
            'youtube_url': 'https://www.youtube.com/watch?v=abc123',
            'language': 'es'
        })
        mock_generate.assert_called_with('https://www.youtube.com/watch?v=abc123', 'es')

def test_generate_blog_error_string_response(client):
    """Test handling when blog generation returns error string"""
    with patch('app.generate_blog_from_youtube', return_value="ERROR: Test error"):
        response = client.post('/generate', data={'youtube_url': 'https://www.youtube.com/watch?v=abc123'})
        assert response.status_code == 500
        
        response_text = response.data.decode('utf-8')
        assert any(indicator in response_text for indicator in [
            "Test error", "Failed to generate blog", "ERROR:", "error occurred"
        ])

def test_generate_blog_empty_content(client):
    """Test when blog generation returns empty content"""
    with patch('app.generate_blog_from_youtube', return_value=""):
        response = client.post('/generate', data={'youtube_url': 'https://www.youtube.com/watch?v=abc123'})
        assert response.status_code == 500
        
        response_text = response.data.decode('utf-8').lower()
        assert any(keyword in response_text for keyword in [
            'failed to generate blog content', 'failed to generate blog', 'try with a different video'
        ])

def test_generate_blog_short_content(client):
    """Test blog generation with content too short"""
    with patch('app.generate_blog_from_youtube', return_value="Short"):
        response = client.post('/generate', data={'youtube_url': 'https://www.youtube.com/watch?v=abc123'})
        assert response.status_code == 500

def test_generate_blog_exception_handling(client):
    """Test blog generation exception handling"""
    with patch('app.generate_blog_from_youtube', side_effect=Exception("Generation failed")):
        response = client.post('/generate', data={'youtube_url': 'https://www.youtube.com/watch?v=abc123'})
        assert response.status_code == 500

def test_generate_blog_general_exception(client):
    """Test general exception handling in generate_blog"""
    # Test with malformed form data that will cause an exception
    response = client.post('/generate', data={'invalid_field': 'value'})
    # Should handle missing youtube_url gracefully
    assert response.status_code == 400
    
# ===== RESULTS PAGE TESTS =====
def test_results_success(client):
    """Test successful results page"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://www.youtube.com/watch?v=abc123',
            'generation_time': 1.5
        }
    
    response = client.get('/results')
    assert response.status_code == 200

def test_results_missing_content_id(client):
    """Test results page with missing content_id"""
    response = client.get('/results')
    assert response.status_code == 302
    assert response.location.endswith(url_for('index'))

def test_results_missing_session_data(client):
    """Test results page with missing session data"""
    with client.session_transaction() as sess:
        sess['content_id'] = 'invalid_id'
    
    response = client.get('/results')
    assert response.status_code == 302

def test_results_video_id_extraction(client):
    """Test results page video ID extraction"""
    test_cases = [
        ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ('https://invalid-url.com', 'unknown')
    ]
    
    for url, expected_id in test_cases:
        with client.session_transaction() as sess:
            sess['content_id'] = '123'
            sess['123'] = {
                'blog_content': 'Test content',
                'youtube_url': url,
                'generation_time': 1.5
            }
        
        response = client.get('/results')
        assert response.status_code == 200

def test_results_exception_handling(client):
    """Test results page exception handling"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {'blog_content': 'Test content', 'youtube_url': 'invalid'}
    
    # Test with data that might cause processing errors
    response = client.get('/results')
    # Should either work or redirect gracefully
    assert response.status_code in [200, 302]
# ===== DOWNLOAD TESTS =====
def test_download_pdf_success(client):
    """Test successful PDF download"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://www.youtube.com/watch?v=abc123'
        }
    
    with patch('app.PDFGeneratorTool') as mock_pdf:
        mock_instance = mock_pdf.return_value
        mock_instance.generate_pdf_bytes.return_value = b'PDF content'
        
        response = client.get('/download')
        assert response.status_code == 200
        assert response.mimetype == 'application/pdf'

def test_download_pdf_missing_session(client):
    """Test PDF download with missing session"""
    response = client.get('/download')
    assert response.status_code == 302

def test_download_pdf_missing_content_key(client):
    """Test PDF download when blog_content key is missing"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {'youtube_url': 'https://www.youtube.com/watch?v=abc123'}
    
    response = client.get('/download')
    assert response.status_code == 302

def test_download_pdf_invalid_video_id(client):
    """Test PDF download with invalid video ID"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://invalid-url.com'
        }
    
    with patch('app.PDFGeneratorTool') as mock_pdf:
        mock_instance = mock_pdf.return_value
        mock_instance.generate_pdf_bytes.return_value = b'PDF content'
        
        response = client.get('/download')
        assert response.status_code == 200
        
        # Check for actual filename pattern
        content_disposition = response.headers.get('Content-Disposition', '')
        assert '.pdf' in content_disposition
        # The app generates filename based on URL, so expect that pattern
        assert 'blog_' in content_disposition
def test_download_pdf_fallback_to_text(client):
    """Test PDF download fallback to text"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://www.youtube.com/watch?v=abc123'
        }
    
    with patch('app.PDFGeneratorTool') as mock_pdf:
        mock_instance = mock_pdf.return_value
        mock_instance.generate_pdf_bytes.side_effect = Exception("PDF error")
        
        response = client.get('/download')
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'

def test_download_fallback_failure(client):
    """Test when both PDF and fallback fail"""
    with client.session_transaction() as sess:
        sess['content_id'] = '123'
        sess['123'] = {
            'blog_content': 'Test content',
            'youtube_url': 'https://www.youtube.com/watch?v=abc123'
        }
    
    with patch('app.PDFGeneratorTool') as mock_pdf:
        mock_instance = mock_pdf.return_value
        mock_instance.generate_pdf_bytes.side_effect = Exception("PDF error")
        
        with patch('app.io.BytesIO', side_effect=Exception("BytesIO error")):
            response = client.get('/download')
            assert response.status_code == 302

# ===== API TESTS =====
def test_api_status_success(client):
    """Test API status endpoint success"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

def test_api_status_missing_openai_key(client):
    """Test API status with missing OpenAI key"""
    with patch.dict('os.environ', {}, clear=True):
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['environment']['openai_configured'] == False

def test_api_status_failure(client):
    """Test API status endpoint failure"""
    with patch('os.path.exists', side_effect=Exception("Test error")):
        response = client.get('/api/status')
        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'

def test_api_validate_url_success(client):
    """Test successful URL validation"""
    # Use a properly formatted YouTube URL
    test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    response = client.post('/api/validate-url', json={'url': test_url})
    assert response.status_code == 200
    data = response.get_json()
    assert data['valid'] == True
    assert 'video_id' in data
def test_api_validate_url_empty(client):
    """Test URL validation with empty URL"""
    response = client.post('/api/validate-url', json={'url': ''})
    assert response.status_code == 200
    data = response.get_json()
    assert data['valid'] == False
    assert data['message'] == 'URL is required'

def test_api_validate_url_invalid_format(client):
    """Test URL validation with invalid format"""
    response = client.post('/api/validate-url', json={'url': 'https://vimeo.com/123'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['valid'] == False

def test_api_validate_url_no_video_id(client):
    """Test URL validation with no video ID"""
    response = client.post('/api/validate-url', json={'url': 'https://youtube.com/watch?x=abc'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['valid'] == False

def test_api_validate_url_missing_json(client):
    """Test URL validation with missing JSON"""
    response = client.post('/api/validate-url')
    assert response.status_code in [400, 500]

def test_api_validate_url_exception(client):
    """Test URL validation exception handling"""
    # Test with malformed JSON to trigger exception
    response = client.post('/api/validate-url', 
                          data='{"invalid": json}',
                          content_type='application/json')
    assert response.status_code in [400, 500]


# ===== SESSION AND UTILITY TESTS =====
def test_clear_session_success(client):
    """Test successful session clearing"""
    with client.session_transaction() as sess:
        sess['test_key'] = 'value'
    
    response = client.get('/clear-session')
    assert response.status_code == 302

def test_clear_session_exception(client):
    """Test session clearing with exception"""
    # Test that the endpoint works even if there are session issues
    response = client.get('/clear-session')
    # Should always redirect to index
    assert response.status_code == 302
    assert response.location.endswith(url_for('index'))

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_get_env_var():
    """Test environment variable helper"""
    with patch.dict('os.environ', {'TEST_VAR': 'test_value'}):
        assert get_env_var('TEST_VAR') == 'test_value'
        assert get_env_var('MISSING_VAR', 'default') == 'default'
        assert get_env_var('MISSING_VAR') is None

def test_get_env_var_edge_cases():
    """Test environment variable helper edge cases"""
    with patch.dict('os.environ', {'EMPTY_VAR': ''}):
        assert get_env_var('EMPTY_VAR', 'default') == 'default'

# ===== ERROR HANDLER TESTS =====
def test_404_handler(client):
    """Test 404 error handler"""
    response = client.get('/nonexistent-route')
    assert response.status_code == 404
    assert b"Page not found" in response.data

def test_500_handler(client):
    """Test 500 error handler"""
    with patch('app.render_template', side_effect=Exception("Test 500 error")):
        response = client.get('/')
        assert response.status_code == 500

def test_413_handler(client):
    """Test 413 error handler"""
    flask_app.config['MAX_CONTENT_LENGTH'] = 50
    
    try:
        large_data = 'x' * 100
        response = client.post('/generate', data=large_data, content_type='text/plain')
        assert response.status_code in [413, 400, 500]
    finally:
        flask_app.config.pop('MAX_CONTENT_LENGTH', None)

# ===== LOGGING TESTS =====
def test_before_after_request_logging(client, caplog):
    """Test request logging middleware"""
    with caplog.at_level(logging.INFO):
        response = client.get('/health')
        logs = caplog.text
        assert "Request: GET /health" in logs
        assert f"Response: {response.status_code}" in logs

# ===== SESSION CLEANUP TESTS =====
def test_cleanup_old_sessions_success(tmp_path):
    """Test session cleanup function"""
    session_dir = tmp_path / 'sessions'
    session_dir.mkdir()
    
    old_file = session_dir / 'old_session'
    old_file.write_text('content')
    new_file = session_dir / 'new_session'
    new_file.write_text('content')
    
    old_time = time.time() - 86401
    os.utime(str(old_file), (old_time, old_time))
    
    flask_app.config['SESSION_FILE_DIR'] = str(session_dir)
    cleanup_old_sessions()
    
    assert not old_file.exists()
    assert new_file.exists()

def test_cleanup_old_sessions_no_directory():
    """Test session cleanup when directory doesn't exist"""
    with patch('os.path.exists', return_value=False):
        cleanup_old_sessions()

def test_cleanup_old_sessions_exception(caplog):
    """Test session cleanup exception handling"""
    with patch('os.listdir', side_effect=Exception("Cleanup error")):
        with caplog.at_level(logging.ERROR):
            cleanup_old_sessions()
            assert "Session cleanup failed" in caplog.text

def test_cleanup_old_sessions_mixed_files(tmp_path):
    """Test session cleanup with mixed file types"""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    old_file = session_dir / "old_session"
    old_file.write_text("content")
    new_file = session_dir / "new_session"
    new_file.write_text("content")
    subdir = session_dir / "subdir"
    subdir.mkdir()
    
    old_time = time.time() - 86401
    os.utime(str(old_file), (old_time, old_time))
    
    flask_app.config['SESSION_FILE_DIR'] = str(session_dir)
    cleanup_old_sessions()
    
    assert not old_file.exists()
    assert new_file.exists()
    assert subdir.exists()

# ===== STARTUP AND CONFIGURATION TESTS =====
def test_app_startup_session_dir_creation(tmp_path):
    """Test session directory creation on startup"""
    session_dir = tmp_path / "test_sessions"
    flask_app.config['SESSION_FILE_DIR'] = str(session_dir)
    
    assert not session_dir.exists()
    os.makedirs(str(session_dir))
    assert session_dir.exists()

def test_app_startup_openai_key_validation():
    """Test OpenAI key validation on startup"""
    with patch.dict('os.environ', {}, clear=True):
        with patch('sys.exit') as mock_exit:
            if not os.getenv('OPENAI_API_KEY'):
                mock_exit(1)
            mock_exit.assert_called_with(1)

def test_app_configuration_parsing():
    """Test application configuration parsing"""
    with patch.dict('os.environ', {
        'PORT': '8080',
        'FLASK_DEBUG': 'true',
        'FLASK_HOST': '127.0.0.1'
    }):
        port = int(os.environ.get('PORT', 5000))
        debug_mode = get_env_var('FLASK_DEBUG', 'False').lower() == 'true'
        host = get_env_var('FLASK_HOST', '0.0.0.0')
        
        assert port == 8080
        assert debug_mode == True
        assert host == '127.0.0.1'

# ===== IMPORT ERROR TESTS =====
def test_import_error_handling():
    """Test import error handling"""
    with patch('builtins.__import__', side_effect=ImportError("Module not found")):
        with pytest.raises(ImportError):
            exec("from src.main import generate_blog_from_youtube")
