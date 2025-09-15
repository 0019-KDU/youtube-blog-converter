import pytest
from unittest.mock import patch, MagicMock

class TestValidators:
    
    def test_validate_youtube_url(self):
        """Test YouTube URL validation"""
        from app.utils.validators import validate_youtube_url
        
        # Valid URLs
        assert validate_youtube_url('https://www.youtube.com/watch?v=test') is True
        assert validate_youtube_url('https://youtu.be/test') is True
        assert validate_youtube_url('http://youtube.com/watch?v=test') is True
        
        # Invalid URLs
        assert validate_youtube_url('https://vimeo.com/test') is False
        assert validate_youtube_url('not-a-url') is False
        assert validate_youtube_url('') is False
        assert validate_youtube_url(None) is False
    
    def test_extract_video_id(self):
        """Test video ID extraction"""
        from app.utils.validators import extract_video_id
        
        # Valid video IDs
        assert extract_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
        assert extract_video_id('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
        assert extract_video_id('https://youtube.com/embed/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
        
        # Invalid URLs
        assert extract_video_id('https://vimeo.com/123') is None
        assert extract_video_id('') is None
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        from app.utils.validators import sanitize_filename
        
        assert sanitize_filename('Test File Name') == 'Test-File-Name'
        assert sanitize_filename('Test@#$%File') == 'TestFile'
        assert sanitize_filename('   spaces   ') == 'spaces'
        assert sanitize_filename('') == 'untitled'
        assert sanitize_filename(None) == 'untitled'
        assert sanitize_filename('a' * 100) == 'a' * 50

class TestRateLimiter:
    
    def test_rate_limiter_allows_requests(self, app):
        """Test rate limiter allows requests within limits"""
        from app.utils.rate_limiter import RateLimiter
        
        with app.test_request_context():
            limiter = RateLimiter(requests_per_minute=2)
            
            assert limiter.is_allowed('test_id') is True
            assert limiter.is_allowed('test_id') is True
            assert limiter.is_allowed('test_id') is False  # Exceeds limit
    
    def test_rate_limiter_cleanup(self, app):
        """Test rate limiter cleans old entries"""
        from app.utils.rate_limiter import RateLimiter
        import time
        
        with app.test_request_context():
            limiter = RateLimiter(requests_per_minute=1)
            
            # Add a request
            limiter.is_allowed('test_id')
            
            # Mock time passing
            with patch('time.time', return_value=time.time() + 61):
                assert limiter.is_allowed('test_id') is True  # Should allow after minute

class TestSecurity:
    
    @patch('app.models.user.User')
    @patch('app.utils.security.decode_token')
    def test_get_current_user_from_token(self, mock_decode, mock_user_class, app):
        """Test getting current user from JWT token"""
        from app.utils.security import get_current_user
        
        mock_decode.return_value = {'sub': '123'}
        mock_user = mock_user_class.return_value
        mock_user.get_user_by_id.return_value = {
            '_id': '123',
            'username': 'testuser'
        }
        
        with app.test_request_context(headers={'Authorization': 'Bearer test-token'}):
            user = get_current_user()
            
            assert user is not None
            assert user['username'] == 'testuser'
    
    def test_store_and_retrieve_large_data(self, app):
        """Test storing and retrieving large data"""
        from app.utils.security import store_large_data, retrieve_large_data
        
        with app.test_request_context():
            data = {'large': 'data', 'content': 'test' * 1000}
            key = store_large_data('test_key', data, 'user123')
            
            retrieved = retrieve_large_data('test_key', 'user123')
            
            assert retrieved == data
    
    def test_cleanup_old_storage(self, app):
        """Test cleanup of old storage data"""
        from app.utils.security import store_large_data, cleanup_old_storage
        import time
        
        with app.test_request_context():
            # Store data
            store_large_data('old_key', {'data': 'old'}, 'user123')
            
            # Mock old timestamp
            app.temp_storage['user123_old_key']['timestamp'] = time.time() - 3700
            
            cleanup_old_storage()
            
            assert 'user123_old_key' not in app.temp_storage