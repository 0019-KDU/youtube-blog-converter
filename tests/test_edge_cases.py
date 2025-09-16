from unittest.mock import MagicMock, patch

import pytest

class TestEdgeCases:
    
    @patch('app.models.user.mongo_manager')
    def test_user_model_database_error(self, mock_manager):
        """Test user model handling database errors"""
        from app.models.user import User
        
        mock_manager.get_collection.side_effect = Exception("Database error")
        
        user = User()
        result = user.create_user('test', 'test@example.com', 'password')
        
        assert result['success'] is False
        assert 'Database error' in result['message']
    
    @patch('app.services.blog_service.openai_client_context')
    def test_blog_generator_api_error(self, mock_context):
        """Test blog generator handling API errors"""
        from app.services.blog_service import BlogGeneratorTool

        # Set up the context manager mock to raise an exception when entered
        mock_context.side_effect = Exception("API error")

        tool = BlogGeneratorTool()
        # Use a longer transcript to avoid the length check
        long_transcript = "This is a long transcript that should pass the length validation. " * 3
        result = tool._run(long_transcript)

        assert result.startswith('ERROR:')
        assert 'API error' in result
    
    def test_pdf_generator_unicode_handling(self):
        """Test PDF generator with complex Unicode"""
        from app.crew.tools import PDFGeneratorTool
        
        tool = PDFGeneratorTool()
        
        # Test with various Unicode characters
        complex_text = "Test 🔥 emoji → arrows ½ fractions © symbols"
        cleaned = tool._clean_unicode_text(complex_text)
        
        # Should replace or remove problematic characters
        assert '🔥' not in cleaned
        assert '→' not in cleaned or cleaned.count('->') > 0
    
    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_blog_empty_url(self, mock_get_user, client):
        """Test blog generation with empty URL"""
        mock_get_user.return_value = {'_id': '123', 'username': 'test'}
        
        response = client.post('/generate', json={'youtube_url': ''})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_rate_limiter_concurrent_identifiers(self, app):
        """Test rate limiter with multiple identifiers"""
        from app.utils.rate_limiter import RateLimiter
        
        with app.test_request_context():
            limiter = RateLimiter(requests_per_minute=2)
            
            # Different identifiers should have separate limits
            assert limiter.is_allowed('user1') is True
            assert limiter.is_allowed('user2') is True
            assert limiter.is_allowed('user1') is True
            assert limiter.is_allowed('user2') is True
            assert limiter.is_allowed('user1') is False  # user1 exceeded
            assert limiter.is_allowed('user2') is False  # user2 exceeded