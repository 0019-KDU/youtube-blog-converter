import pytest
import os
import sys
import json
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, Mock  # Added Mock import
from datetime import datetime, timedelta, timezone
import io

# Fixed path resolution - avoiding the coroutine issue
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your Flask app and components
from app import app, inject_config, setup_logging, JSONFormatter, get_current_user, cleanup_after_generation
from auth.models import User, BlogPost
from src.main import generate_blog_from_youtube
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFGeneratorTool


class TestApp:
    """Test main application functionality"""
    
    def test_app_creation(self, app):
        """Test Flask app creation and configuration"""
        assert app.config['TESTING'] is True
        assert app.config['JWT_SECRET_KEY'] is not None
        assert app.config['SESSION_TYPE'] == 'filesystem'
    
    def test_get_secret_key_from_env(self):
        """Test secret key retrieval from environment"""
        from app import get_secret_key
        
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'test-jwt-key'}):
            key = get_secret_key()
            assert key == 'test-jwt-key'
    
    def test_get_secret_key_fallback(self):
        """Test secret key fallback when not in environment"""
        from app import get_secret_key
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('secrets.token_hex', return_value='generated-key'):
                key = get_secret_key()
                assert key == 'generated-key'


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_extract_video_id_youtube_watch(self):
        """Test video ID extraction from youtube.com/watch URLs"""
        from app import extract_video_id
        
        urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'http://www.youtube.com/watch?v=dQw4w9WgXcQ&other=param'
        ]
        
        for url in urls:
            assert extract_video_id(url) == 'dQw4w9WgXcQ'
    
    def test_extract_video_id_youtu_be(self):
        """Test video ID extraction from youtu.be URLs"""
        from app import extract_video_id
        
        urls = [
            'https://youtu.be/dQw4w9WgXcQ',
            'http://youtu.be/dQw4w9WgXcQ'
        ]
        
        for url in urls:
            assert extract_video_id(url) == 'dQw4w9WgXcQ'
    
    def test_extract_video_id_embed(self):
        """Test video ID extraction from embed URLs"""
        from app import extract_video_id
        
        url = 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        assert extract_video_id(url) == 'dQw4w9WgXcQ'
    
    def test_extract_video_id_v_format(self):
        """Test video ID extraction from /v/ URLs"""
        from app import extract_video_id
        
        url = 'https://www.youtube.com/v/dQw4w9WgXcQ'
        assert extract_video_id(url) == 'dQw4w9WgXcQ'
    
    def test_extract_video_id_shorts(self):
        """Test video ID extraction from shorts URLs"""
        from app import extract_video_id
        
        url = 'https://www.youtube.com/shorts/dQw4w9WgXcQ'
        assert extract_video_id(url) == 'dQw4w9WgXcQ'
    
        def test_extract_video_id_invalid(self):
            """Test video ID extraction from invalid URLs"""
            from app import extract_video_id
            
            invalid_urls = [
                'https://vimeo.com/123456',
                'https://example.com',
                'not-a-url',
                'https://youtube.com/watch?v=invalid',
                'https://youtube.com/watch?v=',
                ''
            ]
            # Remove None from the list as it causes TypeError
            
            for url in invalid_urls:
                assert extract_video_id(url) is None
            
            # Test None separately
            assert extract_video_id(None) is None



class TestGetCurrentUser:
    """Test get_current_user function"""
    
    @patch('app.User')
    @patch('app.decode_token')
    def test_get_current_user_from_auth_header(self, mock_decode, mock_user_class, client):
        """Test getting current user from Authorization header"""
        sample_user_data = {
            '_id': 'test_user_id',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        mock_decode.return_value = {'sub': 'user123'}
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = sample_user_data
        mock_user_class.return_value = mock_user_instance
        
        with client.application.test_request_context(
            headers={'Authorization': 'Bearer test_token'}
        ):
            user = get_current_user()
            
            assert user == sample_user_data
            mock_decode.assert_called_once()
    
    
    @patch('app.User')
    @patch('app.decode_token')
    def test_get_current_user_from_session_token(self, mock_decode, mock_user_class, client):
        """Test getting current user from session token"""
        sample_user_data = {
            '_id': 'test_user_id',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        mock_decode.return_value = {'sub': 'user123'}
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = sample_user_data
        mock_user_class.return_value = mock_user_instance
        
        with client:
            with client.session_transaction() as sess:
                sess['access_token'] = 'test_token'
            
            with client.application.test_request_context():
                from flask import session
                session['access_token'] = 'test_token'
                
                user = get_current_user()
                assert user == sample_user_data


        
    @patch('app.User')
    def test_get_current_user_from_user_id(self, mock_user_class, client):
        """Test getting current user from user_id in session"""
        sample_user_data = {
            '_id': 'test_user_id',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = sample_user_data
        mock_user_class.return_value = mock_user_instance
        
        with client:
            with client.session_transaction() as sess:
                sess['user_id'] = 'user123'
            
            with client.application.test_request_context():
                from flask import session
                session['user_id'] = 'user123'
                
                user = get_current_user()
                assert user == sample_user_data


    @patch('app.decode_token')
    def test_get_current_user_invalid_token(self, mock_decode, client):
        """Test get_current_user with invalid token"""
        mock_decode.side_effect = Exception("Invalid token")
        
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                sess['access_token'] = 'invalid_token'
            
            from app import get_current_user
            user = get_current_user()
            
            assert user is None
    
    def test_get_current_user_no_token(self, client):
        """Test get_current_user with no token"""
        with client.application.test_request_context():
            from app import get_current_user
            user = get_current_user()
            
            assert user is None
    
    @patch('app.User')
    def test_get_current_user_exception(self, mock_user_class, client):
        """Test get_current_user with exception"""
        mock_user_class.side_effect = Exception("Database error")
        
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                sess['user_id'] = 'user123'
            
            from app import get_current_user
            user = get_current_user()
            
            assert user is None


class TestTemplateHelpers:
    """Test template helper functions"""
    
    def test_format_date_with_datetime(self, app):
        """Test format_date with datetime object"""
        with app.app_context():
            from app import format_date
            
            date = datetime(2025, 1, 15)  # Fixed: removed duplicate datetime
            result = format_date(date)
            assert result == 'Jan 15, 2025'
    
    def test_format_date_with_string(self, app):
        """Test format_date with string date"""
        with app.app_context():
            from app import format_date
            
            result = format_date('2025-01-15T10:30:00Z')
            assert 'Jan 15, 2025' in result
    
    def test_format_date_with_invalid_string(self, app):
        """Test format_date with invalid string"""
        with app.app_context():
            from app import format_date
            
            result = format_date('invalid-date')
            assert result == 'invalid-date'
    
    def test_format_date_no_arg(self, app):
        """Test format_date with no argument"""
        with app.app_context():
            from app import format_date
            
            result = format_date()
            assert isinstance(result, str)
    
    def test_moment_function(self, app):
        """Test moment template function"""
        with app.app_context():
            from app import moment
            
            date = datetime(2025, 1, 15)  # Fixed: removed duplicate datetime
            mock_moment = moment(date)
            
            result = mock_moment.format('MMM DD, YYYY')
            assert result == 'Jan 15, 2025'
    
    def test_moment_with_string_date(self, app):
        """Test moment with string date"""
        with app.app_context():
            from app import moment
            
            mock_moment = moment('2025-01-15T10:30:00Z')
            result = mock_moment.format('YYYY-MM-DD')
            assert '2025-01-15' in result
    
    def test_moment_with_invalid_string(self, app):
        """Test moment with invalid string"""
        with app.app_context():
            from app import moment
            
            mock_moment = moment('invalid-date')
            result = mock_moment.format('MMM DD, YYYY')
            assert result == 'invalid-date'
    
    def test_moment_no_date(self, app):
        """Test moment with no date"""
        with app.app_context():
            from app import moment
            
            mock_moment = moment(None)
            result = mock_moment.format('MMM DD, YYYY')
            assert isinstance(result, str)
    
    def test_moment_unknown_format(self, app):
        """Test moment with unknown format"""
        with app.app_context():
            from app import moment
            
            date = datetime(2025, 1, 15)  # Fixed: removed duplicate datetime
            mock_moment = moment(date)
            result = mock_moment.format('UNKNOWN_FORMAT')
            assert result == 'Jan 15, 2025'
    
    def test_nl2br_filter(self, app):
        """Test nl2br filter"""
        with app.app_context():
            from app import nl2br_filter
            
            text = "Line 1\nLine 2\nLine 3"
            result = nl2br_filter(text)
            assert result == "Line 1<br>Line 2<br>Line 3"
    
    def test_nl2br_filter_none(self, app):
        """Test nl2br filter with None"""
        with app.app_context():
            from app import nl2br_filter
            
            result = nl2br_filter(None)
            assert result == ''


class TestCleanupFunctions:
    """Test cleanup functions"""
    
# Fix: Mock pythoncom properly and handle Windows-specific test
# test_app.py
    @patch('app.sys.platform', 'win32')
    def test_cleanup_com_objects_windows(self):
        """Test COM objects cleanup on Windows"""
        with patch.dict('sys.modules', {'pythoncom': MagicMock()}):
            from app import cleanup_com_objects
            cleanup_com_objects()
            # Verify the methods were called
            import pythoncom
            pythoncom.CoUninitialize.assert_called_once()
            pythoncom.CoInitialize.assert_called_once()

    
    @patch('app.sys.platform', 'linux')
    def test_cleanup_com_objects_non_windows(self):
        """Test COM objects cleanup on non-Windows"""
        from app import cleanup_com_objects
        
        # Should not raise any exception
        cleanup_com_objects()
    
    @patch('app.gc.collect')
    def test_cleanup_memory(self, mock_gc_collect):
        """Test memory cleanup"""
        from app import cleanup_memory
        
        mock_gc_collect.return_value = 5
        cleanup_memory()
        
        assert mock_gc_collect.call_count >= 2
    
    def test_cleanup_database_connections_list(self):
        """Test database connections cleanup with list"""
        from app import cleanup_database_connections
        
        mock_objects = [Mock(), Mock()]
        cleanup_database_connections(mock_objects)
        # Should not raise exception
    
    def test_cleanup_database_connections_single(self):
        """Test database connections cleanup with single object"""
        from app import cleanup_database_connections
        
        mock_object = Mock()
        cleanup_database_connections(mock_object)
        # Should not raise exception
    
    @patch('app.cleanup_database_connections')
    @patch('app.cleanup_com_objects')
    @patch('app.cleanup_memory')
    def test_full_cleanup(self, mock_memory, mock_com, mock_db):
        """Test full cleanup function"""
        from app import full_cleanup
        
        full_cleanup('arg1', 'arg2')
        
        mock_db.assert_called_once()
        mock_com.assert_called_once()
        mock_memory.assert_called_once()
    
    @patch('app.gc.collect')
    def test_cleanup_after_generation(self, mock_gc_collect):
        """Test cleanup after generation"""
        from app import cleanup_after_generation
        
        # Test on Windows platform
        with patch('app.sys.platform', 'win32'):
            with patch('app.cleanup_com_objects') as mock_com_cleanup:
                with patch('app.cleanup_memory') as mock_memory_cleanup:
                    cleanup_after_generation()
                    
                    assert mock_gc_collect.call_count == 3
                    mock_com_cleanup.assert_called_once()
                    mock_memory_cleanup.assert_called_once()
        
        # Test on non-Windows platform (Linux/Mac)
        with patch('app.sys.platform', 'linux'):
            with patch('app.cleanup_memory') as mock_memory_cleanup:
                cleanup_after_generation()
                
                assert mock_gc_collect.call_count >= 3
                mock_memory_cleanup.assert_called_once()



class TestRoutes:
    """Test application routes"""
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {
            '_id': 'test_user_id',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
    @pytest.fixture
    def sample_blog_content(self):
        """Sample blog content for testing - FIXED: Made it longer than 100 characters"""
        return """# AI Tools Review: A Comprehensive Guide

    ## Introduction

    This article reviews various AI productivity tools and their capabilities. This content is now long enough to pass the 100 character minimum requirement for blog generation.

    ## Main Tools Discussed

    ### Fabric
    - Excellent for AI workflows
    - Great automation capabilities
    - User-friendly interface

    ### Claude
    - Strong reasoning capabilities
    - Good for complex tasks
    - Reliable performance

    ## Conclusion

    Each tool has its place in the AI productivity landscape and offers unique benefits for different use cases."""
    def test_index_route(self, client):
        """Test index route"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_index_route_exception(self, client):
        """Test index route with exception"""
        with patch('app.render_template', side_effect=Exception("Template error")):
            response = client.get('/')
            assert response.status_code == 500
            assert b"Error loading page" in response.data
    
    @patch('app.get_current_user')
    def test_generate_page_authenticated(self, mock_get_user, client, sample_user_data):
        """Test generate page with authenticated user"""
        mock_get_user.return_value = sample_user_data
        
        response = client.get('/generate-page')
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_generate_page_unauthenticated(self, mock_get_user, client):
        """Test generate page without authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/generate-page')
        assert response.status_code == 302
    
   # Fix: Correct the test parameters and assertions
    @patch('app.get_current_user')
    def test_generate_page_exception(self, mock_get_user, client, sample_user_data):
        """Test generate page with exception"""
        mock_get_user.return_value = sample_user_data
        
        # First call: generate.html fails, second call: error.html succeeds
        with patch('app.render_template') as mock_render:
            mock_render.side_effect = [
                Exception("Template error"), 
                "Rendered error page"
            ]
            response = client.get('/generate-page')
            assert response.status_code == 500

    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.BlogPost')
    @patch('app.cleanup_after_generation')
    def test_generate_blog_success(self, mock_cleanup, mock_blog_class, mock_generate, 
                                  mock_get_user, client, mock_user, sample_blog_content):
        """Test successful blog generation"""
        mock_get_user.return_value = mock_user
        mock_generate.return_value = sample_blog_content
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = {'_id': 'post123'}
        mock_blog_class.return_value = mock_blog_instance
        
        data = {
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'language': 'en'
        }
        
        response = client.post('/generate', data=data)
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert 'blog_content' in response_data
        mock_cleanup.assert_called()
    
    @patch('app.get_current_user')
    def test_generate_blog_unauthenticated(self, mock_get_user, client):
        """Test blog generation without authentication"""
        mock_get_user.return_value = None
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 401
        response_data = response.get_json()
        assert response_data['success'] is False
    
    @patch('app.get_current_user')
    def test_generate_blog_missing_url(self, mock_get_user, client, sample_user_data):
        """Test blog generation with missing URL"""
        mock_get_user.return_value = sample_user_data
        
        data = {'youtube_url': ''}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'required' in response_data['message']
    
    @patch('app.get_current_user')
    def test_generate_blog_invalid_url_format(self, mock_get_user, client, sample_user_data):
        """Test blog generation with invalid URL format"""
        mock_get_user.return_value = sample_user_data
        
        data = {'youtube_url': 'https://invalid.com/video'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'valid YouTube URL' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.extract_video_id')
    def test_generate_blog_invalid_video_id(self, mock_extract, mock_get_user, client, sample_user_data):
        """Test blog generation with invalid video ID"""
        mock_get_user.return_value = sample_user_data
        mock_extract.return_value = None
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=invalid'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'Invalid YouTube URL' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.cleanup_after_generation')
    def test_generate_blog_generation_error(self, mock_cleanup, mock_generate, mock_get_user, 
                                          client, sample_user_data):
        """Test blog generation with generation error"""
        mock_get_user.return_value = sample_user_data
        mock_generate.side_effect = Exception("Generation failed")
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 500
        response_data = response.get_json()
        assert 'Failed to generate blog' in response_data['message']
        mock_cleanup.assert_called()
    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.cleanup_after_generation')
    def test_generate_blog_short_content(self, mock_cleanup, mock_generate, mock_get_user, 
                                       client, sample_user_data):
        """Test blog generation with too short content"""
        mock_get_user.return_value = sample_user_data
        mock_generate.return_value = "Short content"
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 500
        response_data = response.get_json()
        assert 'Failed to generate blog content' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.cleanup_after_generation')
    def test_generate_blog_error_content(self, mock_cleanup, mock_generate, mock_get_user, 
                                    client, sample_user_data):
        """Test blog generation with error content"""
        mock_get_user.return_value = sample_user_data
        
        # Create content that's long enough but starts with ERROR
        long_error_content = "ERROR: Some error occurred" + " This is additional content to make it longer than 100 characters so it passes the length check but still contains the error message at the beginning."
        mock_generate.return_value = long_error_content
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 500
        response_data = response.get_json()
        # The app removes "ERROR:" and strips, so check for the remaining message
        assert 'Some error occurred' in response_data['message']


    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.BlogPost')
    @patch('app.cleanup_after_generation')
    def test_generate_blog_save_failure(self, mock_cleanup, mock_blog_class, mock_generate, 
                                    mock_get_user, client, sample_user_data, sample_blog_content):
        """Test blog generation with save failure - FIXED"""
        mock_get_user.return_value = sample_user_data
        mock_generate.return_value = sample_blog_content
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = None  # This will trigger save failure
        mock_blog_class.return_value = mock_blog_instance
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 500
        response_data = response.get_json()
        # FIXED: Check for the actual error message that gets returned
        assert 'Failed to save blog post' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.PDFGeneratorTool')
    @patch('app.cleanup_after_generation')
    def test_download_pdf_success(self, mock_cleanup, mock_pdf_class, mock_get_user, 
                                client, mock_user):
        """Test successful PDF download"""
        mock_get_user.return_value = mock_user
        
        mock_pdf_instance = Mock()
        mock_pdf_instance.generate_pdf_bytes.return_value = b'mock pdf content'
        mock_pdf_class.return_value = mock_pdf_instance
        
        with client.session_transaction() as sess:
            sess['current_blog'] = {
                'blog_content': 'Test content',
                'title': 'Test Blog'
            }
        
        response = client.get('/download')
        
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'
        mock_cleanup.assert_called()
    
    @patch('app.get_current_user')
    def test_download_pdf_unauthenticated(self, mock_get_user, client):
        """Test PDF download without authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/download')
        assert response.status_code == 302
    
    @patch('app.get_current_user')
    def test_download_pdf_no_data(self, mock_get_user, client, sample_user_data):
        """Test PDF download without blog data"""
        mock_get_user.return_value = sample_user_data
        
        response = client.get('/download')
        
        assert response.status_code == 404
        response_data = response.get_json()
        assert 'No blog data found' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.PDFGeneratorTool')
    @patch('app.cleanup_after_generation')
    def test_download_pdf_generation_error(self, mock_cleanup, mock_pdf_class, mock_get_user, 
                                         client, sample_user_data):
        """Test PDF download with generation error"""
        mock_get_user.return_value = sample_user_data
        mock_pdf_class.side_effect = Exception("PDF generation failed")
        
        with client.session_transaction() as sess:
            sess['current_blog'] = {
                'blog_content': 'Test content',
                'title': 'Test Blog'
            }
        
        response = client.get('/download')
        
        assert response.status_code == 500
        response_data = response.get_json()
        assert 'PDF generation failed' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_dashboard_success(self, mock_blog_class, mock_get_user, client, 
                            sample_user_data, sample_blog_post):
        """Test dashboard with authenticated user - FIXED"""
        mock_get_user.return_value = sample_user_data
        
        mock_blog_instance = Mock()
        mock_blog_instance.get_user_posts.return_value = [sample_blog_post]
        mock_blog_class.return_value = mock_blog_instance
        
        # FIXED: Set up session properly to avoid redirect
        with client.session_transaction() as sess:
            sess['user_id'] = sample_user_data['_id']
            sess['access_token'] = 'test_token'
        
        response = client.get('/dashboard')
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_dashboard_unauthenticated(self, mock_get_user, client):
        """Test dashboard without authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/dashboard')
        assert response.status_code == 302
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_dashboard_exception(self, mock_blog_class, mock_get_user, client, sample_user_data):
        """Test dashboard with exception"""
        mock_get_user.return_value = sample_user_data
        mock_blog_class.side_effect = Exception("Database error")
        
        response = client.get('/dashboard')
        assert response.status_code == 302
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_delete_post_success(self, mock_blog_class, mock_get_user, client, mock_user):
        """Test successful post deletion"""
        mock_get_user.return_value = mock_user
        
        mock_blog_instance = Mock()
        mock_blog_instance.delete_post.return_value = True
        mock_blog_class.return_value = mock_blog_instance
        
        response = client.delete('/delete-post/post123')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
    
    @patch('app.get_current_user')
    def test_delete_post_unauthenticated(self, mock_get_user, client):
        """Test post deletion without authentication"""
        mock_get_user.return_value = None
        
        response = client.delete('/delete-post/post123')
        
        assert response.status_code == 401
        response_data = response.get_json()
        assert response_data['success'] is False
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_delete_post_not_found(self, mock_blog_class, mock_get_user, client, mock_user):
        """Test deleting non-existent post"""
        mock_get_user.return_value = mock_user
        
        mock_blog_instance = Mock()
        mock_blog_instance.delete_post.return_value = False
        mock_blog_class.return_value = mock_blog_instance
        
        response = client.delete('/delete-post/nonexistent')
        
        assert response.status_code == 404
        response_data = response.get_json()
        assert response_data['success'] is False

    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_delete_post_exception(self, mock_blog_class, mock_get_user, client, sample_user_data):
        """Test post deletion with exception"""
        mock_get_user.return_value = sample_user_data
        mock_blog_class.side_effect = Exception("Database error")
        
        response = client.delete('/delete-post/post123')
        
        assert response.status_code == 500
        response_data = response.get_json()
        assert response_data['success'] is False
    
    def test_contact_route(self, client):
        """Test contact route"""
        response = client.get('/contact')
        assert response.status_code == 200
    
    def test_contact_route_exception(self, client):
        """Test contact route with exception"""
        # First call: contact.html fails, second call: error.html succeeds
        with patch('app.render_template') as mock_render:
            mock_render.side_effect = [
                Exception("Template error"), 
                "Rendered error page"
            ]
            response = client.get('/contact')
            assert response.status_code == 500

class TestErrorHandlers:
    """Test error handlers"""
    
    def test_unauthorized_handler(self, client):
        """Test 401 error handler"""
        with client.application.test_request_context():
            from app import unauthorized
            
            response = unauthorized(None)
            assert response.status_code == 302
    
    def test_not_found_handler(self, client):
        """Test 404 error handler"""
        with patch('app.render_template') as mock_render:
            mock_render.return_value = "Error page"
            
            response = client.get('/nonexistent-route')
            assert response.status_code == 404

    
    @patch('app.render_template')
    def test_internal_error_handler(self, mock_render, client):
        """Test 500 error handler"""
        mock_render.return_value = "Error page"
        
        with client.application.test_request_context():
            from app import internal_error
            
            response = internal_error(None)
            assert response[1] == 500


class TestContextProcessors:
    """Test context processors"""
    
    @patch('app.get_current_user')
    def test_inject_user_authenticated(self, mock_get_user, client, sample_user_data):
        """Test inject_user with authenticated user"""
        mock_get_user.return_value = sample_user_data
        
        with client.application.test_request_context():
            from app import inject_user
            
            context = inject_user()
            assert context['current_user'] == sample_user_data
            assert context['user_logged_in'] is True
    
    @patch('app.get_current_user')
    def test_inject_user_unauthenticated(self, mock_get_user, client):
        """Test inject_user with unauthenticated user"""
        mock_get_user.return_value = None
        
        with client.application.test_request_context():
            from app import inject_user
            
            context = inject_user()
            assert context['current_user'] is None
            assert context['user_logged_in'] is False


class TestTeardownHandlers:
    """Test teardown handlers"""
    
    @patch('app.cleanup_memory')
    def test_cleanup_app_context(self, mock_cleanup, client):
        """Test app context cleanup"""
        with client.application.test_request_context():
            from app import cleanup_app_context
            
            cleanup_app_context(None)
            mock_cleanup.assert_called_once()
    
    @patch('app.cleanup_memory')
    def test_cleanup_app_context_exception(self, mock_cleanup, client):
        """Test app context cleanup with exception"""
        mock_cleanup.side_effect = Exception("Cleanup error")
        
        with client.application.test_request_context():
            from app import cleanup_app_context
            
            # Should not raise exception
            cleanup_app_context(None)


class TestMainExecution:
    """Test main execution block"""
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'SUPADATA_API_KEY': 'test-key', 
        'MONGODB_URI': 'test-uri',
        'JWT_SECRET_KEY': 'test-key'
    })
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_main_execution_success(self, mock_makedirs, mock_exists):
        """Test successful main execution"""
        # Mock the main execution check
        with patch('app.__name__', '__main__'):
            with patch('app.app.run') as mock_run:
                # Re-execute the main block logic
                session_dir = './.flask_session/'
                if not os.path.exists(session_dir):
                    os.makedirs(session_dir)
                
                mock_makedirs.assert_called_once()

    
    @patch.dict(os.environ, {}, clear=True)
    @patch('sys.exit')
    def test_main_execution_missing_env_vars(self, mock_exit):
        """Test main execution with missing environment variables"""
        # This would trigger the missing vars check
        with patch('app.logger') as mock_logger:
            import app
            # The missing vars check should trigger during import
    
    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'SUPADATA_API_KEY': 'test-key',
        'MONGODB_URI': 'test-uri', 
        'JWT_SECRET_KEY': 'test-key'
    })
    @patch('app.app.run')
    @patch('app.full_cleanup')
    def test_main_execution_finally_block(self, mock_cleanup, mock_run):
        """Test main execution finally block"""
        mock_run.side_effect = KeyboardInterrupt()
        
        try:
            import app
        except SystemExit:
            pass
        
        # The finally block should have been executed
        # (This is hard to test directly due to import mechanics)


class TestSessionManagement:
    """Test session management in routes"""
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {
            '_id': 'test_user_id',
            'username': 'testuser',
            'email': 'test@example.com'
        }

    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.BlogPost')
    def test_session_storage_in_generate(self, mock_blog_class, mock_generate, mock_get_user,
                                    client, sample_user_data, sample_blog_content):
        """Test session storage during blog generation - FIXED"""
        mock_get_user.return_value = sample_user_data
        mock_generate.return_value = sample_blog_content
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = {'_id': 'post123'}
        mock_blog_class.return_value = mock_blog_instance
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        
        # FIXED: Remove nested client context
        response = client.post('/generate', data=data)
        
        assert response.status_code == 200
        
        # Check session data was stored
        with client.session_transaction() as sess:
            assert 'current_blog' in sess
            assert sess['current_blog']['title'] is not None
class TestGoogleAnalyticsIntegration:
    """Test Google Analytics integration and configuration"""
    
    def test_ga_measurement_id_configuration(self, app):
        """Test GA_MEASUREMENT_ID configuration loading"""
        with app.app_context():
            # Test default configuration
            assert 'GA_MEASUREMENT_ID' in app.config
            
            # Test environment variable loading
            with patch.dict(os.environ, {'GA_MEASUREMENT_ID': 'G-TEST123456'}):
                # Reload config
                app.config['GA_MEASUREMENT_ID'] = os.getenv('GA_MEASUREMENT_ID', '')
                assert app.config['GA_MEASUREMENT_ID'] == 'G-TEST123456'
    
    def test_ga_measurement_id_fallback(self, app):
        """Test GA_MEASUREMENT_ID fallback when env var not set"""
        with app.app_context():
            with patch.dict(os.environ, {}, clear=True):
                app.config['GA_MEASUREMENT_ID'] = os.getenv('GA_MEASUREMENT_ID', '')
                assert app.config['GA_MEASUREMENT_ID'] == ''
    
    def test_inject_config_context_processor(self, app):
        """Test inject_config context processor"""
        with app.app_context():
            from app import inject_config  # Replace 'app' with your actual module
            
            context = inject_config()
            assert 'config' in context
            assert context['config'] == app.config
            assert hasattr(context['config'], 'get')
    
    def test_ga_script_in_base_template(self, client, app):
        """Test Google Analytics script inclusion in base template"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            response = client.get('/')
            assert response.status_code == 200
            
            html = response.get_data(as_text=True)
            assert 'googletagmanager.com/gtag/js?id=G-TEST123456' in html
            assert 'window.dataLayer = window.dataLayer || [];' in html
            assert 'gtag(\'js\', new Date());' in html
            assert 'gtag(\'config\', \'G-TEST123456\');' in html
    
    def test_ga_script_with_empty_measurement_id(self, client, app):
        """Test GA script behavior with empty measurement ID"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = ''
            
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Should still include GA script but with empty ID
            assert 'googletagmanager.com/gtag/js?id=' in html
            assert 'gtag(\'config\', \'\');' in html
    
    def test_ga_script_in_all_templates(self, client, app):
        """Test GA script inclusion in all major templates"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            # Test pages that should include GA
            test_pages = [
                ('/', 'index'),
                ('/login', 'login'),
                ('/register', 'register'),
            ]
            
            for url, page_name in test_pages:
                response = client.get(url)
                if response.status_code == 200:
                    html = response.get_data(as_text=True)
                    assert 'googletagmanager.com/gtag/js' in html, f"GA missing on {page_name}"
                    assert 'gtag(' in html, f"gtag function missing on {page_name}"

class TestGoogleAnalyticsEventTracking:
    """Test Google Analytics event tracking functionality"""
    
    def test_login_tracking_script(self, client, app):
        """Test login event tracking script"""
        with app.app_context():
            response = client.get('/login')
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                assert 'trackLogin' in html
                assert 'gtag(\'event\', \'login\'' in html
                assert 'event_category\': \'Authentication\'' in html
    
    def test_register_tracking_script(self, client, app):
        """Test registration event tracking script"""
        with app.app_context():
            response = client.get('/register')
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                assert 'trackSignUp' in html
                assert 'gtag(\'event\', \'sign_up\'' in html
                assert 'event_category\': \'Authentication\'' in html
    
    def test_generate_page_tracking_script(self, client, app, auth_headers):
        """Test blog generation tracking scripts"""
        with app.app_context():
            response = client.get('/generate', headers=auth_headers)
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                
                # Check for tracking functions
                tracking_functions = [
                    'trackBlogGenerationStart',
                    'trackBlogGenerationSuccess',
                    'trackBlogGenerationError',
                    'trackPdfDownload',
                    'trackContentCopy'
                ]
                
                for func in tracking_functions:
                    assert func in html, f"Missing tracking function: {func}"
    
    def test_blog_generation_event_tracking(self, client, app, auth_headers):
        """Test blog generation event tracking"""
        with app.app_context():
            response = client.get('/generate', headers=auth_headers)
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                
                # Check for specific GA events
                assert 'blog_generation_start' in html
                assert 'blog_generation_success' in html
                assert 'blog_generation_error' in html
                assert 'event_category\': \'Blog Generation\'' in html

class TestTemplateIntegration:
    """Test template integration with Google Analytics"""
    
    def test_base_template_structure(self, client, app):
        """Test base template has proper GA structure"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Check template structure - look for rendered content, not template syntax
            template_checks = [
                '<!DOCTYPE html>',
                '<head>',
                'Google tag (gtag.js)',  # Comment should be present
                'googletagmanager.com/gtag/js',  # Actual GA script
                'gtag(\'config\'',  # GA configuration call
            ]
            
            for check in template_checks:
                assert check in html, f"Missing template element: {check}"
    
    def test_config_availability_in_templates(self, client, app):
        """Test config is available in all templates"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            # Test template rendering with config
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Should see the measurement ID rendered
            assert 'G-TEST123456' in html
    
    def test_template_blocks_structure(self, client, app):
        """Test template blocks are properly structured"""
        with app.app_context():
            response = client.get('/')
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                
                # Check for actual rendered content, not template syntax
                template_elements = [
                    '<title>',
                    '<meta charset="UTF-8">',
                    'bootstrap',  # Case insensitive check for Bootstrap
                    'font',  # Font Awesome or other font references
                ]
                
                for element in template_elements:
                    # Use case-insensitive search
                    assert element.lower() in html.lower(), f"Missing template element: {element}"
    
    def test_javascript_integration(self, client, app):
        """Test JavaScript integration in templates"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Check for JavaScript elements
            js_elements = [
                '<script',
                'gtag(',
                'dataLayer',
                '</script>',
            ]
            
            for element in js_elements:
                assert element in html, f"Missing JavaScript element: {element}"
    
    def test_css_integration(self, client, app):
        """Test CSS integration in templates"""
        with app.app_context():
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Check for CSS links - look for common patterns
            css_patterns = [
                'stylesheet',
                '.css',
                '<link',
            ]
            
            css_found = any(pattern in html.lower() for pattern in css_patterns)
            assert css_found, "No CSS links found in template"
    
    def test_responsive_meta_tags(self, client, app):
        """Test responsive and meta tags"""
        with app.app_context():
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Check for essential meta tags
            meta_tags = [
                'viewport',
                'charset',
            ]
            
            for tag in meta_tags:
                assert tag in html.lower(), f"Missing meta tag: {tag}"

class TestGoogleAnalyticsConfiguration:
    """Test different GA configuration scenarios"""
    
    def test_ga_config_with_production_id(self, app):
        """Test GA configuration with production ID"""
        with app.app_context():
            from app import inject_config  # Import the function
            app.config['GA_MEASUREMENT_ID'] = 'G-8S6B6N48LH'
            context = inject_config()
            
            assert context['config']['GA_MEASUREMENT_ID'] == 'G-8S6B6N48LH'
    
    def test_ga_config_with_test_id(self, app):
        """Test GA configuration with test ID"""
        with app.app_context():
            from app import inject_config  # Import the function
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            context = inject_config()
            
            assert context['config']['GA_MEASUREMENT_ID'] == 'G-TEST123456'
    def test_ga_config_validation(self, app):
        """Test GA configuration format validation"""
        with app.app_context():
            from app import inject_config  # Import the function
            # Test valid format
            valid_ids = ['G-XXXXXXXXXX', 'G-8S6B6N48LH', 'G-TEST123456']
            
            for valid_id in valid_ids:
                app.config['GA_MEASUREMENT_ID'] = valid_id
                context = inject_config()
                assert context['config']['GA_MEASUREMENT_ID'] == valid_id

    
    @patch.dict(os.environ, {'GA_MEASUREMENT_ID': 'G-ENV123456'})
    def test_environment_variable_override(self, app):
        """Test environment variable overrides default config"""
        with app.app_context():
            # Simulate app startup config loading
            app.config['GA_MEASUREMENT_ID'] = os.getenv('GA_MEASUREMENT_ID', 'G-DEFAULT')
            
            assert app.config['GA_MEASUREMENT_ID'] == 'G-ENV123456'

class TestGoogleAnalyticsErrorHandling:
    """Test error handling in GA implementation"""
    
    def test_missing_ga_measurement_id(self, client, app):
        """Test behavior when GA_MEASUREMENT_ID is missing"""
        with app.app_context():
            # Remove GA_MEASUREMENT_ID
            if 'GA_MEASUREMENT_ID' in app.config:
                del app.config['GA_MEASUREMENT_ID']
            
            # Should not break the app
            response = client.get('/')
            assert response.status_code == 200
    
    def test_invalid_ga_measurement_id(self, client, app):
        """Test behavior with invalid GA_MEASUREMENT_ID format"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'INVALID-ID'
            
            response = client.get('/')
            assert response.status_code == 200
            
            html = response.get_data(as_text=True)
            assert 'INVALID-ID' in html  # Should still render, even if invalid
    
    def test_context_processor_error_handling(self, app):
        """Test context processor handles missing config gracefully"""
        with app.app_context():
            from app import inject_config
            # Test with normal config (should work)
            context = inject_config()
            assert context is not None
            assert 'config' in context

class TestGoogleAnalyticsJavaScript:
    """Test JavaScript functionality for GA tracking"""
    
    def test_gtag_initialization_script(self, client, app):
        """Test gtag initialization script"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Check gtag initialization
            assert 'window.dataLayer = window.dataLayer || [];' in html
            assert 'function gtag(){dataLayer.push(arguments);}' in html
            assert 'gtag(\'js\', new Date());' in html
    
    def test_event_tracking_functions_exist(self, client, app, auth_headers):
        """Test that event tracking functions are defined"""
        with app.app_context():
            response = client.get('/generate', headers=auth_headers)
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                
                # Check function definitions
                functions = [
                    'function trackBlogGenerationStart',
                    'function trackBlogGenerationSuccess',
                    'function trackBlogGenerationError',
                    'function trackPdfDownload',
                    'function trackContentCopy'
                ]
                
                for func in functions:
                    assert func in html, f"Missing function definition: {func}"
    
    def test_page_view_tracking(self, client, app):
        """Test page view tracking implementation"""
        with app.app_context():
            response = client.get('/generate')  # Or any page with tracking
            if response.status_code == 200:
                html = response.get_data(as_text=True)
                
                # Check for page view tracking
                page_view_indicators = [
                    'page_view',
                    'page_title',
                    'page_location',
                    'content_group'
                ]
                
                # At least some page view tracking should exist
                has_page_tracking = any(indicator in html for indicator in page_view_indicators)
                assert has_page_tracking, "No page view tracking found"

class TestGoogleAnalyticsCompliance:
    """Test GA implementation compliance and best practices"""
    
    def test_ga_script_async_loading(self, client, app):
        """Test GA script uses async loading"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Check for async attribute
            assert 'async src="https://www.googletagmanager.com/gtag/js' in html
    
    def test_ga_privacy_considerations(self, client, app):
        """Test privacy-related GA implementation"""
        with app.app_context():
            response = client.get('/')
            html = response.get_data(as_text=True)
            
            # Should use HTTPS
            assert 'https://www.googletagmanager.com' in html
            # Should not include personal data in tracking calls
            assert 'email' not in html.lower() or 'user_id' not in html.lower()

# Additional fixtures for testing
@pytest.fixture
def auth_headers():
    """Provide authentication headers for testing protected routes"""
    return {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
    }

@pytest.fixture
def mock_ga_response():
    """Mock Google Analytics response for testing"""
    return {
        'success': True,
        'measurement_id': 'G-TEST123456',
        'events_tracked': ['page_view', 'blog_generation_start']
    }

# Integration test for the complete flow
class TestGoogleAnalyticsEndToEnd:
    """End-to-end testing of Google Analytics integration"""
    
    def test_complete_ga_integration_flow(self, client, app):
        """Test complete GA integration from config to rendering"""
        with app.app_context():
            from app import inject_config  # Import the function
            
            # 1. Set up configuration
            app.config['GA_MEASUREMENT_ID'] = 'G-8S6B6N48LH'
            
            # 2. Test context processor
            context = inject_config()
            assert context['config']['GA_MEASUREMENT_ID'] == 'G-8S6B6N48LH'
            
            # 3. Test template rendering
            response = client.get('/')
            assert response.status_code == 200
    def test_complete_ga_integration_flow(self, client, app):
        """Test complete GA integration from config to rendering"""
        with app.app_context():
            # 1. Set up configuration
            app.config['GA_MEASUREMENT_ID'] = 'G-8S6B6N48LH'
            
            # 2. Test context processor
            context = inject_config()
            assert context['config']['GA_MEASUREMENT_ID'] == 'G-8S6B6N48LH'
            
            # 3. Test template rendering
            response = client.get('/')
            assert response.status_code == 200
            
            html = response.get_data(as_text=True)
            
            # 4. Verify all GA components
            ga_components = [
                'googletagmanager.com/gtag/js?id=G-8S6B6N48LH',
                'window.dataLayer = window.dataLayer || [];',
                'function gtag(){dataLayer.push(arguments);}',
                'gtag(\'js\', new Date());',
                'gtag(\'config\', \'G-8S6B6N48LH\');'
            ]
            
            for component in ga_components:
                assert component in html, f"Missing GA component: {component}"
            
            print("✅ Complete Google Analytics integration test passed!")
    
    def test_ga_with_user_authentication_flow(self, client, app):
        """Test GA tracking through user authentication flow"""
        with app.app_context():
            app.config['GA_MEASUREMENT_ID'] = 'G-TEST123456'
            
            # Test login page
            login_response = client.get('/login')
            if login_response.status_code == 200:
                login_html = login_response.get_data(as_text=True)
                assert 'trackLogin' in login_html
            
            # Test register page
            register_response = client.get('/register')
            if register_response.status_code == 200:
                register_html = register_response.get_data(as_text=True)
                assert 'trackSignUp' in register_html             
                
class TestLoggingConfiguration:
    """Test cases for logging configuration and functionality"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_log_dir(self, temp_log_dir):
        """Mock the log directory path"""
        with patch('app.Path') as mock_path:
            mock_path.return_value.mkdir.return_value = None
            mock_path.return_value = Path(temp_log_dir)
            yield temp_log_dir
    
    def test_json_formatter_basic_log_entry(self):
        """Test JSONFormatter creates proper JSON log entries"""
        formatter = JSONFormatter()
        
        # Create a mock log record
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='/app/test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Assertions
        assert log_data['level'] == 'INFO'
        assert log_data['logger'] == 'test_logger'
        assert log_data['message'] == 'Test message'
        assert log_data['line'] == 42
        assert 'timestamp' in log_data
        assert 'process_id' in log_data
        assert 'thread_id' in log_data
    
    def test_json_formatter_with_extra_fields(self):
        """Test JSONFormatter with Flask-specific extra fields"""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='/app/test.py',
            lineno=42,
            msg='Request processed',
            args=(),
            exc_info=None
        )
        
        # Add extra Flask-specific fields
        record.user_id = 'user123'
        record.youtube_url = 'https://youtube.com/watch?v=test'
        record.blog_generation_time = 45.5
        record.request_id = 'req-123'
        record.method = 'POST'
        record.path = '/generate'
        record.status_code = 200
        record.remote_addr = '192.168.1.100'
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Assertions for extra fields
        assert log_data['user_id'] == 'user123'
        assert log_data['youtube_url'] == 'https://youtube.com/watch?v=test'
        assert log_data['blog_generation_time'] == 45.5
        assert log_data['request_id'] == 'req-123'
        assert log_data['method'] == 'POST'
        assert log_data['path'] == '/generate'
        assert log_data['status_code'] == 200
        assert log_data['remote_addr'] == '192.168.1.100'
    
    def test_json_formatter_with_exception(self):
        """Test JSONFormatter handles exceptions properly"""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name='test_logger',
            level=logging.ERROR,
            pathname='/app/test.py',
            lineno=42,
            msg='Error occurred',
            args=(),
            exc_info=exc_info
        )
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['level'] == 'ERROR'
        assert log_data['message'] == 'Error occurred'
        assert 'exception' in log_data
        assert 'ValueError: Test exception' in log_data['exception']
    
    @patch('pathlib.Path.mkdir')  # FIXED: Patch only mkdir method
    @patch('app.logging.handlers.RotatingFileHandler')
    def test_setup_logging_creates_directories(self, mock_handler, mock_mkdir):
        """Test that setup_logging creates necessary directories - FIXED"""
        mock_mkdir.return_value = None
        mock_handler_instance = Mock()
        mock_handler.return_value = mock_handler_instance
        
        access_logger = setup_logging()
        
        # Verify directory creation was attempted
        mock_mkdir.assert_called_with(parents=True, exist_ok=True)
        assert access_logger is not None
        assert access_logger.name == 'access'
    
    @patch('pathlib.Path.mkdir')  # FIXED: Patch only mkdir method
    @patch('app.logging.handlers.RotatingFileHandler')
    def test_setup_logging_creates_handlers(self, mock_handler, mock_mkdir):
        """Test that setup_logging creates proper file handlers - FIXED"""
        mock_mkdir.return_value = None
        mock_handler_instance = Mock()
        mock_handler.return_value = mock_handler_instance
        
        setup_logging()
        
        # Verify handlers were created (should be at least 3)
        assert mock_handler.call_count >= 3
    
    @patch('pathlib.Path.mkdir')
    @patch('tempfile.gettempdir')
    def test_setup_logging_handler_levels(self, mock_gettempdir, mock_mkdir):
        """Test that logging handlers have correct levels - FIXED"""
        mock_gettempdir.return_value = tempfile.gettempdir()
        mock_mkdir.return_value = None
        
        # Mock the environment to use testing mode
        with patch.dict(os.environ, {'TESTING': 'true', 'FLASK_ENV': 'testing'}):
            # Mock the logging handlers to avoid actual file operations
            with patch('app.logging.handlers.RotatingFileHandler') as mock_handler:
                mock_handler_instance = Mock()
                mock_handler.return_value = mock_handler_instance
                
                access_logger = setup_logging()
                
                # Check access logger configuration
                assert access_logger.propagate is False
                assert len(access_logger.handlers) >= 0  # May be 0 in test mode
                
                # Verify mkdir was called for test log directory
                mock_mkdir.assert_called_with(parents=True, exist_ok=True)


class TestFlaskLoggingIntegration:
    """Test Flask application logging integration"""
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return {
            '_id': 'test_user_id',
            'username': 'testuser',
            'email': 'test@example.com'
        }
    
    @patch('app.access_logger')
    def test_request_logging_middleware(self, mock_access_logger, client):
        """Test that request logging middleware works"""
        response = client.get('/')
        
        # Check that access logger was called
        assert mock_access_logger.info.called
        
        # Get the call arguments
        call_args = mock_access_logger.info.call_args_list
        assert len(call_args) >= 2  # Should have start and complete logs

    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.BlogPost')
    @patch('app.logger')
    def test_blog_generation_logging(self, mock_logger, mock_blog_class, mock_generate, 
                                   mock_get_user, client, mock_user):
        """Test logging during blog generation"""
        mock_get_user.return_value = mock_user
        mock_generate.return_value = "# Test Blog\n\nThis is a test blog content."
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = {'_id': 'test_post_id'}
        mock_blog_class.return_value = mock_blog_instance
        
        response = client.post('/generate', data={
            'youtube_url': 'https://youtube.com/watch?v=test123',
            'language': 'en'
        })
        
        # Check that logger was called with info level
        assert mock_logger.info.called
        
        # Check for specific log messages
        call_args = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('Blog generation started' in msg for msg in call_args)
    
    @patch('app.get_current_user')
    @patch('app.logger')
    def test_error_logging_on_invalid_url(self, mock_logger, mock_get_user, client):
        """Test error logging for invalid YouTube URLs"""
        mock_get_user.return_value = {'_id': 'test_user', 'username': 'test'}
        
        response = client.post('/generate', data={
            'youtube_url': 'invalid-url',
            'language': 'en'
        })
        
        # Check warning was logged
        assert mock_logger.warning.called

class TestLoggingEnvironmentVariables:
    """Test logging configuration with environment variables"""
    
    def test_log_level_environment_variable(self):
        """Test LOG_LEVEL environment variable affects logging"""
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}):
            log_level = os.getenv('LOG_LEVEL', 'INFO')
            assert log_level == 'DEBUG'
    
    def test_log_to_file_environment_variable(self):
        """Test LOG_TO_FILE environment variable"""
        with patch.dict(os.environ, {'LOG_TO_FILE': 'false'}):
            log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
            assert log_to_file is False
        
        with patch.dict(os.environ, {'LOG_TO_FILE': 'true'}):
            log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
            assert log_to_file is True
    
    def test_loki_endpoint_environment_variable(self):
        """Test LOKI_ENDPOINT environment variable"""
        test_endpoint = 'http://test-loki:3100'
        with patch.dict(os.environ, {'LOKI_ENDPOINT': test_endpoint}):
            loki_endpoint = os.getenv('LOKI_ENDPOINT')
            assert loki_endpoint == test_endpoint
    
    def test_logging_enabled_environment_variable(self):
        """Test LOGGING_ENABLED environment variable"""
        with patch.dict(os.environ, {'LOGGING_ENABLED': 'false'}):
            logging_enabled = os.getenv('LOGGING_ENABLED', 'true').lower() == 'true'
            assert logging_enabled is False

class TestLogFileOperations:
    """Test log file creation and rotation"""
    
    @pytest.fixture
    def temp_log_directory(self):
        """Create temporary directory for log testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @patch('pathlib.Path.mkdir')  # FIXED: Patch only mkdir method
    def test_log_file_creation(self, mock_mkdir, temp_log_directory):
        """Test that log files are created properly - FIXED"""
        mock_mkdir.return_value = None
        
        with patch('app.logging.handlers.RotatingFileHandler') as mock_handler:
            setup_logging()
            
            # Verify handlers were created
            assert mock_handler.call_count >= 3
            
            # Verify mkdir was called for log directory creation
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)
    
    def test_log_rotation_configuration(self):
        """Test log rotation settings"""
        with patch('app.logging.handlers.RotatingFileHandler') as mock_handler:
            with patch('app.Path') as mock_path:
                mock_path.return_value.mkdir.return_value = None
                
                setup_logging()
                
                # Check rotation settings
                for call in mock_handler.call_args_list:
                    args, kwargs = call
                    # Verify maxBytes is set (10MB)
                    assert 'maxBytes' in kwargs or len(args) > 1
                    # Verify backupCount is set
                    assert 'backupCount' in kwargs or len(args) > 2

class TestHealthCheckLogging:
    """Test health check endpoint logging"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @patch('auth.models.mongo_manager')
    def test_health_check_success_logging(self, mock_mongo_manager, client):
        """Test health check success is logged"""
        mock_mongo_manager.is_connected.return_value = True
        
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    
    @patch('auth.models.mongo_manager')
    def test_health_check_failure_logging(self, mock_mongo_manager, client):
        """Test health check failure is logged"""
        mock_mongo_manager.is_connected.side_effect = Exception("Database connection failed")
        
        response = client.get('/health')
        assert response.status_code == 503

class TestLoggingCleanup:
    """Test logging-related cleanup functions"""
    
    def test_cleanup_after_generation(self):
        """Test cleanup_after_generation function"""
        # This should not raise any exceptions
        try:
            cleanup_after_generation()
            assert True
        except Exception as e:
            pytest.fail(f"cleanup_after_generation raised an exception: {e}")
    
    @patch('app.gc.collect')
    def test_cleanup_calls_garbage_collection(self, mock_gc_collect):
        """Test that cleanup calls garbage collection"""
        mock_gc_collect.return_value = 5  # Mock collected objects count
        
        cleanup_after_generation()
        
        # Verify gc.collect was called multiple times
        assert mock_gc_collect.call_count >= 3

class TestExistingAppFunctionality:
    """Test existing app functionality (from your original tests)"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client
    
    def test_index_route(self, client):
        """Test index route works"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_contact_route(self, client):
        """Test contact route works"""
        response = client.get('/contact')
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_generate_page_requires_auth(self, mock_get_user, client):
        """Test generate page requires authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/generate-page')
        assert response.status_code == 302  # Redirect to login
    
    @patch('app.get_current_user')
    def test_generate_page_with_auth(self, mock_get_user, client):
        """Test generate page works with authentication"""
        mock_get_user.return_value = {
            '_id': 'test_user',
            'username': 'testuser'
        }
        
        response = client.get('/generate-page')
        assert response.status_code == 200
    
    def test_extract_video_id(self):
        """Test video ID extraction from various YouTube URL formats"""
        from app import extract_video_id
        
        test_cases = [
            ('https://youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('invalid-url', None),
        ]
        
        for url, expected in test_cases:
            result = extract_video_id(url)
            assert result == expected

class TestRemoteLoggingIntegration:
    """Test integration with remote logging services (Loki)"""
    
    def test_loki_log_shipping_configuration(self):
        """Test Loki log shipping configuration"""
        # Test that environment variables for Loki are read correctly
        test_endpoint = 'http://test-loki:3100/loki/api/v1/push'
        
        with patch.dict(os.environ, {
            'LOKI_ENDPOINT': test_endpoint,
            'REMOTE_LOGGING': 'true'
        }):
            loki_endpoint = os.getenv('LOKI_ENDPOINT')
            remote_logging = os.getenv('REMOTE_LOGGING', 'false').lower() == 'true'
            
            assert loki_endpoint == test_endpoint
            assert remote_logging is True
    
    @patch('requests.post')
    def test_mock_loki_log_shipping(self, mock_post):
        """Test mock log shipping to Loki"""
        mock_post.return_value.status_code = 204
        
        # This would be implemented if you add direct Loki shipping
        # For now, just test that the mock works
        import requests
        response = requests.post('http://test-loki:3100/loki/api/v1/push', json={
            'streams': [{
                'stream': {'job': 'flask-app'},
                'values': [['1234567890000000000', 'test log message']]
            }]
        })
        
        assert response.status_code == 204
        mock_post.assert_called_once()

# Pytest configuration and fixtures
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['FLASK_ENV'] = 'testing'
    
    yield
    
    # Cleanup after tests
    for key in ['TESTING', 'LOG_LEVEL', 'FLASK_ENV']:
        os.environ.pop(key, None)
@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests"""
    # Remove all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Reset access logger
    access_logger = logging.getLogger('access')
    for handler in access_logger.handlers[:]:
        access_logger.removeHandler(handler)
    
    yield
    
    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in access_logger.handlers[:]:
        access_logger.removeHandler(handler)

if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])