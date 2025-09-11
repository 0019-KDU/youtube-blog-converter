import json
from unittest.mock import Mock, patch

import pytest
import requests


class TestYouTubeTranscriptTool:
    """Test cases for YouTubeTranscriptTool"""
    
    def test_init_success(self):
        """Test successful initialization"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        with patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'}):
            tool = YouTubeTranscriptTool()
            assert tool is not None
    
    # Update the test_init_missing_api_key method
    def test_init_missing_api_key(self):
        """Test initialization with missing API key"""
        from app.services.youtube_service import YouTubeTranscriptTool

        # Fix: Properly patch the SUPADATA_API_KEY at module level
        with patch('app.services.youtube_service.SUPADATA_API_KEY', None):
            with pytest.raises(RuntimeError, match="Supadata API key not configured"):
                YouTubeTranscriptTool()

    
    def test_run_success(self, mock_requests_session):
        """Test successful transcript extraction"""
        from app.services.youtube_service import YouTubeTranscriptTool

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'content': 'Test transcript content'}
        mock_response.raise_for_status.return_value = None
        mock_requests_session.get.return_value = mock_response
        
        with patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'}), \
             patch('app.services.youtube_service.requests.Session', return_value=mock_requests_session):
            
            tool = YouTubeTranscriptTool()
            result = tool._run('https://www.youtube.com/watch?v=test123', 'en')
            
            assert result == 'Test transcript content'
            mock_requests_session.get.assert_called_once()
    
    def test_run_http_error(self, mock_requests_session):
        """Test transcript extraction with HTTP error"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_requests_session.get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        with patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'}), \
             patch('app.services.youtube_service.requests.Session', return_value=mock_requests_session):
            
            tool = YouTubeTranscriptTool()
            result = tool._run('https://www.youtube.com/watch?v=test123', 'en')
            
            assert result.startswith('ERROR: HTTP error')
    
    def test_run_request_exception(self, mock_requests_session):
        """Test transcript extraction with request exception"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_requests_session.get.side_effect = requests.exceptions.RequestException("Connection error")
        
        with patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'}), \
             patch('app.services.youtube_service.requests.Session', return_value=mock_requests_session):
            
            tool = YouTubeTranscriptTool()
            result = tool._run('https://www.youtube.com/watch?v=test123', 'en')
            
            assert result.startswith('ERROR: Request failed')
    
    def test_run_invalid_json(self, mock_requests_session):
        """Test transcript extraction with invalid JSON response"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_requests_session.get.return_value = mock_response
        
        with patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'}), \
             patch('app.services.youtube_service.requests.Session', return_value=mock_requests_session):
            
            tool = YouTubeTranscriptTool()
            result = tool._run('https://www.youtube.com/watch?v=test123', 'en')
            
            assert result.startswith('ERROR: Invalid response')
    
    def test_run_missing_content(self, mock_requests_session):
        """Test transcript extraction with missing content in response"""
        from app.services.youtube_service import YouTubeTranscriptTool
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'error': 'No transcript available'}
        mock_response.raise_for_status.return_value = None
        mock_requests_session.get.return_value = mock_response
        
        with patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'}), \
             patch('app.services.youtube_service.requests.Session', return_value=mock_requests_session):
            
            tool = YouTubeTranscriptTool()
            result = tool._run('https://www.youtube.com/watch?v=test123', 'en')
            
            assert result.startswith('ERROR: Transcript not found')