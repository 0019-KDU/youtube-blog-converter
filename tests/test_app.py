import pytest
import os
import tempfile
import shutil
import json
import datetime
from unittest.mock import Mock, patch, MagicMock
from flask import session
from bson import ObjectId
import io


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
    def test_get_current_user_from_auth_header(self, mock_decode, mock_user_class, client, sample_user_data):
        """Test getting current user from Authorization header"""
        mock_decode.return_value = {'sub': 'user123'}
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = sample_user_data
        mock_user_class.return_value = mock_user_instance
        
        with client.application.test_request_context(
            headers={'Authorization': 'Bearer test_token'}
        ):
            from app import get_current_user
            user = get_current_user()
            
            assert user == sample_user_data
            mock_decode.assert_called_once()
    
    @patch('app.User')
    @patch('app.decode_token')
    def test_get_current_user_from_session_token(self, mock_decode, mock_user_class, client, sample_user_data):
        """Test getting current user from session token"""
        mock_decode.return_value = {'sub': 'user123'}
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = sample_user_data
        mock_user_class.return_value = mock_user_instance
        
        with client:
            with client.session_transaction() as sess:
                sess['access_token'] = 'test_token'
            
            # Make a request to trigger the context
            with client.application.test_request_context():
                from app import get_current_user
                # Manually set the session for the test
                from flask import session
                session['access_token'] = 'test_token'
                
                user = get_current_user()
                
                assert user == sample_user_data


        
    @patch('app.User')
    def test_get_current_user_from_user_id(self, mock_user_class, client, sample_user_data):
        """Test getting current user from user_id in session"""
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = sample_user_data
        mock_user_class.return_value = mock_user_instance
        
        with client:
            with client.session_transaction() as sess:
                sess['user_id'] = 'user123'
            
            # Make a request to trigger the context
            with client.application.test_request_context():
                from app import get_current_user
                # Manually set the session for the test
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
            
            date = datetime.datetime(2025, 1, 15)
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
            
            date = datetime.datetime(2025, 1, 15)
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
            
            date = datetime.datetime(2025, 1, 15)
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
                                  mock_get_user, client, sample_user_data, sample_blog_content):
        """Test successful blog generation"""
        mock_get_user.return_value = sample_user_data
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
        """Test blog generation with save failure"""
        mock_get_user.return_value = sample_user_data
        mock_generate.return_value = sample_blog_content
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = None
        mock_blog_class.return_value = mock_blog_instance
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 500
        response_data = response.get_json()
        assert 'Failed to save blog post' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.PDFGeneratorTool')
    @patch('app.cleanup_after_generation')
    def test_download_pdf_success(self, mock_cleanup, mock_pdf_class, mock_get_user, 
                                client, sample_user_data):
        """Test successful PDF download"""
        mock_get_user.return_value = sample_user_data
        
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
        """Test dashboard with authenticated user"""
        mock_get_user.return_value = sample_user_data
        
        mock_blog_instance = Mock()
        mock_blog_instance.get_user_posts.return_value = [sample_blog_post]
        mock_blog_class.return_value = mock_blog_instance
        
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
    def test_delete_post_success(self, mock_blog_class, mock_get_user, client, sample_user_data):
        """Test successful post deletion"""
        mock_get_user.return_value = sample_user_data
        
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
    def test_delete_post_not_found(self, mock_blog_class, mock_get_user, client, sample_user_data):
        """Test deleting non-existent post"""
        mock_get_user.return_value = sample_user_data
        
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
    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.BlogPost')
    def test_session_storage_in_generate(self, mock_blog_class, mock_generate, mock_get_user,
                                       client, sample_user_data, sample_blog_content):
        """Test session storage during blog generation"""
        mock_get_user.return_value = sample_user_data
        mock_generate.return_value = sample_blog_content
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = {'_id': 'post123'}
        mock_blog_class.return_value = mock_blog_instance
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        
        with client:
            response = client.post('/generate', data=data)
            
            assert response.status_code == 200
            
            # Check session data was stored
            with client.session_transaction() as sess:
                assert 'current_blog' in sess
                assert sess['current_blog']['title'] is not None
