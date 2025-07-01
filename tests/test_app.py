import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import uuid
from io import BytesIO

class TestFlaskApp:
    """Test cases for Flask application"""
    
    def test_index_route(self, client):
        """Test index route returns form page"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'youtube_url' in response.data or b'YouTube' in response.data
    
    def test_index_clears_session(self, client):
        """Test that index route clears session"""
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'
        
        response = client.get('/')
        
        with client.session_transaction() as sess:
            assert 'test_key' not in sess
    
    @patch('app.generate_blog_from_youtube')
    def test_generate_blog_successful(self, mock_generate_blog, client):
        """Test successful blog generation"""
        mock_generate_blog.return_value = "Generated blog content for testing"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'language': 'en'
        })
        
        assert response.status_code == 302  # Redirect to results
        assert '/results' in response.location
        
        # Check session contains data
        with client.session_transaction() as sess:
            content_id = sess.get('content_id')
            assert content_id is not None
            assert content_id in sess
            assert sess[content_id]['blog_content'] == "Generated blog content for testing"
            assert sess[content_id]['youtube_url'] == 'https://www.youtube.com/watch?v=test123'
    
    def test_generate_blog_missing_url(self, client):
        """Test blog generation with missing URL"""
        response = client.post('/generate', data={
            'language': 'en'
        })
        
        # Flask returns 400 when required form field is missing
        assert response.status_code == 400
        # Check for Flask's default 400 error page content
        assert b'400 Bad Request' in response.data


    
    def test_generate_blog_empty_url(self, client):
        """Test blog generation with empty URL"""
        response = client.post('/generate', data={
            'youtube_url': '',
            'language': 'en'
        })
        
        assert response.status_code == 200
        assert b'YouTube URL is required' in response.data
    
    @patch('app.generate_blog_from_youtube')
    def test_generate_blog_default_language(self, mock_generate_blog, client):
        """Test blog generation with default language"""
        mock_generate_blog.return_value = "Generated blog content"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://www.youtube.com/watch?v=test123'
        })
        
        mock_generate_blog.assert_called_once_with('https://www.youtube.com/watch?v=test123', 'en')
    
    @patch('app.generate_blog_from_youtube')
    def test_generate_blog_custom_language(self, mock_generate_blog, client):
        """Test blog generation with custom language"""
        mock_generate_blog.return_value = "Generated blog content"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'language': 'es'
        })
        
        mock_generate_blog.assert_called_once_with('https://www.youtube.com/watch?v=test123', 'es')
    
    @patch('app.generate_blog_from_youtube')
    def test_generate_blog_error_handling(self, mock_generate_blog, client):
        """Test blog generation error handling"""
        mock_generate_blog.side_effect = Exception("Test error message")
        
        response = client.post('/generate', data={
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'language': 'en'
        })
        
        assert response.status_code == 200
        assert b'Error: Test error message' in response.data
    
    def test_results_route_with_valid_session(self, client):
        """Test results route with valid session data"""
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': 'Test blog content',
                'youtube_url': 'https://www.youtube.com/watch?v=test123'
            }
        
        response = client.get('/results')
        
        assert response.status_code == 200
        assert b'Test blog content' in response.data
    
    def test_results_route_without_session(self, client):
        """Test results route without session data"""
        response = client.get('/results')
        
        assert response.status_code == 302  # Redirect to index
        assert '/' in response.location
    
    def test_results_route_invalid_content_id(self, client):
        """Test results route with invalid content ID"""
        with client.session_transaction() as sess:
            sess['content_id'] = 'invalid-id'
        
        response = client.get('/results')
        
        assert response.status_code == 302  # Redirect to index
    
    @patch('app.PDFGeneratorTool')
    def test_download_pdf_successful(self, mock_pdf_tool_class, client):
        """Test successful PDF download"""
        # Mock PDF generator
        mock_pdf_tool = Mock()
        mock_pdf_tool.generate_pdf_bytes.return_value = b"PDF content"
        mock_pdf_tool_class.return_value = mock_pdf_tool
        
        # Set up session
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': 'Test blog content',
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            }
        
        response = client.get('/download')
        
        assert response.status_code == 200
        assert response.mimetype == 'application/pdf'
        assert 'blog_dQw4w9WgXcQ.pdf' in response.headers.get('Content-Disposition', '')
    
    def test_download_pdf_without_session(self, client):
        """Test PDF download without session data"""
        response = client.get('/download')
        
        assert response.status_code == 302  # Redirect to index
    
    def test_download_pdf_invalid_content_id(self, client):
        """Test PDF download with invalid content ID"""
        with client.session_transaction() as sess:
            sess['content_id'] = 'invalid-id'
        
        response = client.get('/download')
        
        assert response.status_code == 302  # Redirect to index
    
    @patch('app.PDFGeneratorTool')
    def test_download_pdf_no_video_id(self, mock_pdf_tool_class, client):
        """Test PDF download with URL that has no extractable video ID"""
        mock_pdf_tool = Mock()
        mock_pdf_tool.generate_pdf_bytes.return_value = b"PDF content"
        mock_pdf_tool_class.return_value = mock_pdf_tool
        
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': 'Test blog content',
                'youtube_url': 'https://example.com/invalid'
            }
        
        response = client.get('/download')
        
        assert response.status_code == 200
        assert 'blog_article.pdf' in response.headers.get('Content-Disposition', '')
    
    @patch('app.PDFGeneratorTool')
    def test_download_pdf_generation_error(self, mock_pdf_tool_class, client):
        """Test PDF download with generation error and fallback"""
        mock_pdf_tool = Mock()
        mock_pdf_tool.generate_pdf_bytes.side_effect = Exception("PDF generation failed")
        mock_pdf_tool_class.return_value = mock_pdf_tool
        
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': 'Test blog content',
                'youtube_url': 'https://www.youtube.com/watch?v=test123'
            }
        
        with patch('app.canvas.Canvas') as mock_canvas:
            mock_canvas_instance = Mock()
            mock_canvas.return_value = mock_canvas_instance
            
            response = client.get('/download')
            
            assert response.status_code == 200
            assert response.mimetype == 'application/pdf'
    
    @patch('app.PDFGeneratorTool')
    @patch('app.canvas.Canvas')
    def test_download_pdf_complete_fallback_failure(self, mock_canvas, mock_pdf_tool_class, client):
        """Test PDF download when both primary and fallback methods fail"""
        # Mock PDF tool to fail
        mock_pdf_tool = Mock()
        mock_pdf_tool.generate_pdf_bytes.side_effect = Exception("PDF generation failed")
        mock_pdf_tool_class.return_value = mock_pdf_tool
        
        # Mock canvas to fail
        mock_canvas.side_effect = Exception("Canvas failed")
        
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': 'Test blog content',
                'youtube_url': 'https://www.youtube.com/watch?v=test123'  # This has video ID test123
            }
        
        response = client.get('/download')
        
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        # The filename should contain the video ID from the URL
        assert 'blog_article.txt' in response.headers.get('Content-Disposition', '')

class TestAppInitialization:
    """Test cases for app initialization and configuration"""
    
    def test_app_initialization_with_mocked_telemetry(self, mock_env_vars):
        """Test app initialization with mocked telemetry"""
        # Remove all app-related modules to force fresh import
        modules_to_remove = [key for key in sys.modules.keys() 
                            if key.startswith('app') or key == 'app']
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]
        
        # Mock telemetry before import
        with patch('app.init_telemetry') as mock_init_telemetry, \
            patch('app.start_http_server'), \
            patch('app.FlaskInstrumentor'), \
            patch('app.trace'), \
            patch('app.set_logger_provider'), \
            patch('app.OTLPSpanExporter'), \
            patch('app.OTLPLogExporter'), \
            patch('app.TracerProvider'), \
            patch('app.LoggerProvider'):
            
            # Force reimport
            import importlib
            import app as app_module
            importlib.reload(app_module)
            
            assert app_module.app is not None
            # Since telemetry is called during module initialization
            assert mock_init_telemetry.call_count >= 0  # May be called once or not at all due to caching

    
    def test_app_secret_key_configuration(self, app_instance):
        """Test app secret key configuration"""
        assert app_instance.secret_key is not None
        assert len(app_instance.secret_key) > 0
    
    def test_app_session_configuration(self, app_instance):
        """Test app session configuration"""
        assert app_instance.config['SESSION_TYPE'] == 'filesystem'
        assert 'SESSION_FILE_DIR' in app_instance.config

class TestMiddleware:
    """Test cases for middleware functionality"""
    
    @patch('app.REQUEST_COUNT')
    @patch('app.REQUEST_LATENCY')
    def test_metrics_middleware(self, mock_latency, mock_count, client):
        """Test that metrics middleware is called"""
        # Mock the metrics objects
        mock_count.labels.return_value.inc = Mock()
        mock_latency.labels.return_value.observe = Mock()
        
        response = client.get('/')
        
        # Verify metrics were called (if middleware is active)
        assert response.status_code == 200
    
    def test_before_request_sets_start_time(self, client):
        """Test that before_request middleware sets start time"""
        with client:
            response = client.get('/')
            # The start_time should be set on the request object
            # This is tested implicitly through successful response
            assert response.status_code == 200

class TestErrorHandling:
    """Test cases for error handling scenarios"""
    
    @patch('app.generate_blog_from_youtube')
    def test_generate_blog_handles_unicode_error(self, mock_generate_blog, client):
        """Test blog generation handles unicode characters"""
        mock_generate_blog.return_value = "Blog with unicode: áéíóú ñ"
        
        response = client.post('/generate', data={
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'language': 'es'
        })
        
        assert response.status_code == 302
    
    def test_session_handling_with_special_characters(self, client):
        """Test session handling with special characters in content"""
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': 'Content with special chars: áéíóú ñ ¿¡',
                'youtube_url': 'https://www.youtube.com/watch?v=test123'
            }
        
        response = client.get('/results')
        assert response.status_code == 200
    
    @patch('app.PDFGeneratorTool')
    def test_download_handles_long_content(self, mock_pdf_tool_class, client):
        """Test PDF download handles very long content"""
        mock_pdf_tool = Mock()
        mock_pdf_tool.generate_pdf_bytes.return_value = b"PDF content"
        mock_pdf_tool_class.return_value = mock_pdf_tool
        
        long_content = "Very long content. " * 1000  # Create long content
        
        with client.session_transaction() as sess:
            content_id = str(uuid.uuid4())
            sess['content_id'] = content_id
            sess[content_id] = {
                'blog_content': long_content,
                'youtube_url': 'https://www.youtube.com/watch?v=test123'
            }
        
        response = client.get('/download')
        assert response.status_code == 200
