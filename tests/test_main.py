import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import re
from src.main import (
    generate_blog_from_youtube, 
    _extract_video_id, 
    _is_video_related,
    cli_main
)

class TestExtractVideoId:
    """Test cases for video ID extraction"""
    
    def test_extract_video_id_youtube_watch(self):
        """Test video ID extraction from youtube.com/watch URLs"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = _extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_with_parameters(self):
        """Test video ID extraction with additional parameters"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLtest"
        video_id = _extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_youtu_be(self):
        """Test video ID extraction from youtu.be URLs"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = _extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_embed(self):
        """Test video ID extraction from embed URLs"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = _extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_shorts(self):
        """Test video ID extraction from shorts URLs"""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        video_id = _extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid_url(self):
        """Test video ID extraction with invalid URL"""
        url = "https://example.com/invalid"
        video_id = _extract_video_id(url)
        assert video_id is None
    
    def test_extract_video_id_empty_url(self):
        """Test video ID extraction with empty URL"""
        video_id = _extract_video_id("")
        assert video_id is None

class TestIsVideoRelated:
    """Test cases for video content validation"""
    
    def test_is_video_related_valid_content(self):
        """Test validation with valid video-related content"""
        # Create content that meets the requirements: >500 chars and >=2 indicators
        content = """
        This comprehensive transcript discusses the main topics covered in the video presentation.
        The speaker explains various concepts and mentions important points throughout the discussion.
        According to the presenter, these ideas are crucial for understanding the subject matter.
        The video content provides valuable insights into the topic and the transcript captures
        all the key information shared during this educational presentation. The discussion
        covers multiple aspects of the subject and provides detailed explanations of complex concepts.
        """
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = _is_video_related(content, youtube_url)
        assert result is True
    
    def test_is_video_related_insufficient_indicators(self):
        """Test validation with insufficient video indicators"""
        content = "This is just some random text without video-related content."
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = _is_video_related(content, youtube_url)
        assert result is False
    
    def test_is_video_related_too_short(self):
        """Test validation with content that's too short"""
        content = "Short content"
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = _is_video_related(content, youtube_url)
        assert result is False
    
    def test_is_video_related_empty_content(self):
        """Test validation with empty content"""
        content = ""
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = _is_video_related(content, youtube_url)
        assert result is False
    
    def test_is_video_related_none_content(self):
        """Test validation with None content"""
        content = None
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = _is_video_related(content, youtube_url)
        assert result is False
    
    def test_is_video_related_multiple_indicators(self):
        """Test validation with multiple video indicators"""
        # Create content with multiple indicators and sufficient length
        content = """
        This is a comprehensive transcript from the video where the presenter delivers an engaging presentation.
        The speaker mentions various concepts and explains them in detail throughout the discussion.
        According to the video content, these points are essential for understanding the subject matter discussed.
        The transcript captures all the important information shared during this educational video presentation.
        The discussion covers multiple aspects and the speaker provides detailed explanations of the concepts.
        This video discusses important topics and the presenter explains various ideas in great detail.
        The content of this video transcript shows how the speaker addresses different aspects of the subject.
        """
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = _is_video_related(content, youtube_url)
        assert result is True

class TestGenerateBlogFromYoutube:
    """Test cases for main blog generation function"""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('src.main.create_agents')
    @patch('src.main.create_tasks')
    @patch('src.main.Crew')
    def test_generate_blog_successful(self, mock_crew_class, mock_create_tasks, mock_create_agents):
        """Test successful blog generation"""
        # Mock agents
        mock_transcriber = Mock()
        mock_writer = Mock()
        mock_create_agents.return_value = (mock_transcriber, mock_writer)
        
        # Mock tasks
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_create_tasks.return_value = (mock_transcript_task, mock_blog_task)
        
        # Mock crew with content that passes video relation check
        mock_crew_instance = Mock()
        mock_result = Mock()
        mock_result.raw = """This is a comprehensive blog article about the video content. The transcript discusses 
        important topics and the speaker explains various concepts in detail according to the presenter. 
        This video content provides valuable insights and the discussion covers multiple aspects of the subject.
        The presenter mentions key points throughout the video and explains complex concepts clearly."""
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance
        
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        language = "en"
        
        result = generate_blog_from_youtube(youtube_url, language)
        
        assert "comprehensive blog article" in result
        mock_create_agents.assert_called_once()
        mock_create_tasks.assert_called_once_with(mock_transcriber, mock_writer, youtube_url, language)
        mock_crew_class.assert_called_once()
        mock_crew_instance.kickoff.assert_called_once()
    
    def test_generate_blog_missing_api_key(self):
        """Test error handling when OpenAI API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            youtube_url = "https://www.youtube.com/watch?v=test123"
            
            with pytest.raises(RuntimeError) as exc_info:
                generate_blog_from_youtube(youtube_url)
            
            assert "OpenAI API key not found" in str(exc_info.value)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    def test_generate_blog_invalid_url(self):
        """Test error handling with invalid YouTube URL"""
        invalid_urls = [
            "",
            "https://example.com/video",
            "not-a-url",
            "https://vimeo.com/123456"
        ]
        
        for invalid_url in invalid_urls:
            with pytest.raises(ValueError) as exc_info:
                generate_blog_from_youtube(invalid_url)
            
            assert "Invalid YouTube URL" in str(exc_info.value)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('src.main.create_agents')
    def test_generate_blog_agent_creation_error(self, mock_create_agents):
        """Test error handling when agent creation fails"""
        mock_create_agents.side_effect = Exception("Agent creation failed")
        
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        with pytest.raises(Exception) as exc_info:
            generate_blog_from_youtube(youtube_url)
        
        assert "Agent creation failed" in str(exc_info.value)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('src.main.create_agents')
    @patch('src.main.create_tasks')
    @patch('src.main.Crew')
    def test_generate_blog_crew_execution_error(self, mock_crew_class, mock_create_tasks, mock_create_agents):
        """Test error handling when crew execution fails"""
        # Mock agents and tasks
        mock_create_agents.return_value = (Mock(), Mock())
        mock_create_tasks.return_value = (Mock(), Mock())
        
        # Mock crew to raise exception
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff.side_effect = Exception("Crew execution failed")
        mock_crew_class.return_value = mock_crew_instance
        
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        with pytest.raises(Exception) as exc_info:
            generate_blog_from_youtube(youtube_url)
        
        assert "Crew execution failed" in str(exc_info.value)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('src.main.create_agents')
    @patch('src.main.create_tasks')
    @patch('src.main.Crew')
    def test_generate_blog_result_without_raw_attribute(self, mock_crew_class, mock_create_tasks, mock_create_agents):
        """Test handling result without raw attribute"""
        # Mock agents and tasks
        mock_create_agents.return_value = (Mock(), Mock())
        mock_create_tasks.return_value = (Mock(), Mock())
        
        # Mock crew with result that doesn't have raw attribute but has sufficient content
        mock_crew_instance = Mock()
        mock_result = """This is a comprehensive blog article about video content. The transcript discusses 
        important topics and the speaker explains various concepts according to the presenter. 
        This video provides valuable insights and the discussion covers the subject matter thoroughly."""
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance
        
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        result = generate_blog_from_youtube(youtube_url)
        
        assert result == mock_result
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'})
    @patch('src.main.create_agents')
    @patch('src.main.create_tasks')
    @patch('src.main.Crew')
    @patch('src.main._is_video_related')
    def test_generate_blog_insufficient_video_relation(self, mock_is_video_related, mock_crew_class, mock_create_tasks, mock_create_agents):
        """Test warning when generated content is not sufficiently video-related"""
        # Mock agents and tasks
        mock_create_agents.return_value = (Mock(), Mock())
        mock_create_tasks.return_value = (Mock(), Mock())
        
        # Mock crew
        mock_crew_instance = Mock()
        mock_result = Mock()
        mock_result.raw = "Generic content not related to video"
        mock_crew_instance.kickoff.return_value = mock_result
        mock_crew_class.return_value = mock_crew_instance
        
        # Mock video relation check to return False
        mock_is_video_related.return_value = False
        
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        with patch('src.main.logger') as mock_logger:
            result = generate_blog_from_youtube(youtube_url)
            
            # Should still return result but log warning
            assert result == "Generic content not related to video"
            mock_logger.warning.assert_called_once()

class TestCliMain:
    """Test cases for CLI interface"""
    
    @patch('builtins.input')
    @patch('src.main.generate_blog_from_youtube')
    @patch('builtins.print')
    def test_cli_main_successful(self, mock_print, mock_generate_blog, mock_input):
        """Test successful CLI execution"""
        mock_input.side_effect = [
            "https://www.youtube.com/watch?v=test123",
            "en"
        ]
        mock_generate_blog.return_value = "Generated blog content for testing purposes"
        
        cli_main()
        
        mock_generate_blog.assert_called_once_with("https://www.youtube.com/watch?v=test123", "en")
        mock_print.assert_called()
    
    @patch('builtins.input')
    @patch('src.main.generate_blog_from_youtube')
    @patch('builtins.print')
    def test_cli_main_default_language(self, mock_print, mock_generate_blog, mock_input):
        """Test CLI with default language"""
        mock_input.side_effect = [
            "https://www.youtube.com/watch?v=test123",
            ""  # Empty input for language
        ]
        mock_generate_blog.return_value = "Generated blog content"
        
        cli_main()
        
        mock_generate_blog.assert_called_once_with("https://www.youtube.com/watch?v=test123", "en")
    
    @patch('builtins.input')
    @patch('src.main.generate_blog_from_youtube')
    @patch('builtins.print')
    def test_cli_main_with_error(self, mock_print, mock_generate_blog, mock_input):
        """Test CLI error handling"""
        mock_input.side_effect = [
            "https://www.youtube.com/watch?v=test123",
            "en"
        ]
        mock_generate_blog.side_effect = Exception("Test error")
        
        cli_main()
        
        # Should print error message
        error_calls = [call for call in mock_print.call_args_list if 'Error:' in str(call)]
        assert len(error_calls) > 0
    
    @patch('builtins.input')
    @patch('src.main.generate_blog_from_youtube')
    @patch('builtins.print')
    def test_cli_main_strips_whitespace(self, mock_print, mock_generate_blog, mock_input):
        """Test that CLI strips whitespace from inputs"""
        mock_input.side_effect = [
            "  https://www.youtube.com/watch?v=test123  ",
            "  en  "
        ]
        mock_generate_blog.return_value = "Generated blog content"
        
        cli_main()
        
        mock_generate_blog.assert_called_once_with("https://www.youtube.com/watch?v=test123", "en")
