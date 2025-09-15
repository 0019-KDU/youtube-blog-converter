import pytest
from unittest.mock import patch, MagicMock, mock_open

class TestYouTubeTranscriptTool:
    
    @patch('app.services.youtube_service.requests.Session')
    def test_run_success(self, mock_session_class):
        """Test successful transcript extraction"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_session = mock_session_class.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'content': 'Test transcript content'}
        mock_session.get.return_value = mock_response
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=test')
        
        assert result == 'Test transcript content'
    
    @patch('app.services.youtube_service.requests.Session')
    def test_run_no_content(self, mock_session_class):
        """Test transcript extraction with no content"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_session = mock_session_class.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_session.get.return_value = mock_response
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=test')
        
        assert result.startswith('ERROR:')

class TestBlogGeneratorTool:
    
    @patch('app.services.youtube_service.requests.Session')
    def test_run_success(self, mock_session_class):
        """Test successful transcript extraction"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_session = mock_session_class.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {'content': 'Test transcript content'}
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=test')
        
        assert result == 'Test transcript content'
        mock_session.get.assert_called_once()
    
    def test_run_invalid_transcript(self):
        """Test blog generation with invalid transcript"""
        from app.services.blog_service import BlogGeneratorTool
        
        tool = BlogGeneratorTool()
        result = tool._run('Short')
        
        assert result.startswith('ERROR:')
    
    def test_clean_markdown_content(self):
        """Test markdown content cleaning"""
        from app.services.blog_service import BlogGeneratorTool
        
        tool = BlogGeneratorTool()
        
        input_content = """
        **Bold Text**
        *Italic Text*
        ### Heading
        - List item
        ```code block```
        """
        
        result = tool._clean_markdown_content(input_content)
        
        assert '**' not in result
        assert '*Italic' not in result
        assert '### Heading' in result
        assert '- List item' in result
        assert '```' not in result

class TestAuthService:
    
    @patch('app.services.auth_service.User')
    @patch('app.services.auth_service.decode_token')
    def test_get_current_user_with_token(self, mock_decode, mock_user_class, app):
        """Test getting current user with JWT token"""
        from app.services.auth_service import AuthService
        
        mock_decode.return_value = {'sub': '123'}
        mock_user = mock_user_class.return_value
        mock_user.get_user_by_id.return_value = {
            '_id': '123',
            'username': 'testuser'
        }
        
        with app.test_request_context(headers={'Authorization': 'Bearer test-token'}):
            user = AuthService.get_current_user()
            
            assert user is not None
            assert user['username'] == 'testuser'
    
    @patch('app.services.auth_service.User')
    def test_get_current_user_with_session(self, mock_user_class, app):
        """Test getting current user from session"""
        from app.services.auth_service import AuthService
        
        mock_user = mock_user_class.return_value
        mock_user.get_user_by_id.return_value = {
            '_id': '123',
            'username': 'testuser'
        }
        
        with app.test_request_context():
            from flask import session
            session['user_id'] = '123'
            
            user = AuthService.get_current_user()
            
            assert user is not None
            assert user['username'] == 'testuser'
