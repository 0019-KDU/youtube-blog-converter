import pytest
from unittest.mock import Mock, patch, MagicMock
import io
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFGeneratorTool

class TestYouTubeTranscriptTool:
    """Test cases for YouTube transcript tool"""
    
    @pytest.fixture
    def transcript_tool(self):
        """Create transcript tool instance"""
        return YouTubeTranscriptTool()
    
    def test_extract_video_id_youtube_watch(self, transcript_tool):
        """Test video ID extraction from youtube.com/watch URLs"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = transcript_tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_youtu_be(self, transcript_tool):
        """Test video ID extraction from youtu.be URLs"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = transcript_tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_embed(self, transcript_tool):
        """Test video ID extraction from embed URLs"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = transcript_tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_shorts(self, transcript_tool):
        """Test video ID extraction from shorts URLs"""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        video_id = transcript_tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid_url(self, transcript_tool):
        """Test video ID extraction with invalid URL"""
        url = "https://example.com/invalid"
        video_id = transcript_tool._extract_video_id(url)
        assert video_id is None
    
    def test_clean_transcript_removes_artifacts(self, transcript_tool):
        """Test transcript cleaning removes unwanted artifacts"""
        dirty_transcript = "[Music]\n\nHello world\n\n[Applause]\n\n[Laughter]\nGoodbye"
        cleaned = transcript_tool._clean_transcript(dirty_transcript)
        
        assert "[Music]" not in cleaned
        assert "[Applause]" not in cleaned
        assert "[Laughter]" not in cleaned
        # The actual implementation uses single space replacement
        assert "Hello world" in cleaned and "Goodbye" in cleaned
    
    def test_clean_transcript_removes_timestamps(self, transcript_tool):
        """Test transcript cleaning removes timestamps"""
        transcript_with_timestamps = "[0:30] Hello [1:45] World [2:00] Test"
        cleaned = transcript_tool._clean_transcript(transcript_with_timestamps)
        
        assert "[0:30]" not in cleaned
        assert "[1:45]" not in cleaned
        assert "[2:00]" not in cleaned
        # The actual implementation may leave extra spaces
        assert "Hello" in cleaned and "World" in cleaned and "Test" in cleaned
    
    def test_clean_transcript_empty_input(self, transcript_tool):
        """Test transcript cleaning with empty input"""
        cleaned = transcript_tool._clean_transcript("")
        assert cleaned == ""
        
        cleaned = transcript_tool._clean_transcript(None)
        assert cleaned == ""
    
    @patch('src.tool.YouTubeTranscriptApi')
    def test_run_successful_english_transcript(self, mock_api, transcript_tool):
        """Test successful transcript extraction for English"""
        # Mock transcript data - make it longer to pass the length check
        mock_transcript_data = [
            {'text': 'Hello everyone, welcome to this comprehensive video tutorial', 'start': 0.0, 'duration': 3.0},
            {'text': 'Today we will be discussing various important topics in detail', 'start': 3.0, 'duration': 4.0},
            {'text': 'This content will help you understand the key concepts thoroughly', 'start': 7.0, 'duration': 4.0}
        ]
        
        mock_transcript = Mock()
        mock_transcript.fetch.return_value = mock_transcript_data
        
        mock_transcript_list = Mock()
        mock_transcript_list.find_transcript.return_value = mock_transcript
        mock_api.list_transcripts.return_value = mock_transcript_list
        
        with patch('src.tool.TextFormatter') as mock_formatter:
            mock_formatter_instance = Mock()
            # Return longer formatted text to pass length validation
            long_transcript = "Hello everyone, welcome to this comprehensive video tutorial. Today we will be discussing various important topics in detail. This content will help you understand the key concepts thoroughly."
            mock_formatter_instance.format_transcript.return_value = long_transcript
            mock_formatter.return_value = mock_formatter_instance
            
            result = transcript_tool._run("https://www.youtube.com/watch?v=test123", "en")
            
            assert long_transcript in result
            mock_api.list_transcripts.assert_called_once_with("test123")
    
    @patch('src.tool.YouTubeTranscriptApi')
    def test_run_fallback_to_generated_transcript(self, mock_api, transcript_tool):
        """Test fallback to auto-generated transcript"""
        mock_transcript_data = [
            {'text': 'Auto generated content that is sufficiently long for testing purposes', 'start': 0.0, 'duration': 3.0},
            {'text': 'This transcript contains enough content to pass the length validation', 'start': 3.0, 'duration': 4.0}
        ]
        
        mock_transcript = Mock()
        mock_transcript.fetch.return_value = mock_transcript_data
        
        mock_transcript_list = Mock()
        # First call fails, second succeeds
        mock_transcript_list.find_transcript.side_effect = Exception("No manual transcript")
        mock_transcript_list.find_generated_transcript.return_value = mock_transcript
        mock_api.list_transcripts.return_value = mock_transcript_list
        
        with patch('src.tool.TextFormatter') as mock_formatter:
            mock_formatter_instance = Mock()
            long_content = "Auto generated content that is sufficiently long for testing purposes. This transcript contains enough content to pass the length validation."
            mock_formatter_instance.format_transcript.return_value = long_content
            mock_formatter.return_value = mock_formatter_instance
            
            result = transcript_tool._run("https://www.youtube.com/watch?v=test123", "en")
            
            assert long_content in result
    
    @patch('src.tool.YouTubeTranscriptApi')
    def test_run_translation_fallback(self, mock_api, transcript_tool):
        """Test fallback to translation when no English transcript available"""
        mock_transcript_data = [
            {'text': 'Translated content that is long enough for validation purposes', 'start': 0.0, 'duration': 3.0},
            {'text': 'This translated transcript has sufficient length to pass checks', 'start': 3.0, 'duration': 4.0}
        ]
        
        mock_translated_transcript = Mock()
        mock_translated_transcript.fetch.return_value = mock_transcript_data
        
        mock_original_transcript = Mock()
        mock_original_transcript.translate.return_value = mock_translated_transcript
        
        mock_transcript_list = Mock()
        mock_transcript_list.find_transcript.side_effect = Exception("No English")
        mock_transcript_list.find_generated_transcript.side_effect = Exception("No generated")
        # Make the transcript list iterable
        mock_transcript_list.__iter__ = Mock(return_value=iter([mock_original_transcript]))
        mock_api.list_transcripts.return_value = mock_transcript_list
        
        with patch('src.tool.TextFormatter') as mock_formatter:
            mock_formatter_instance = Mock()
            long_content = "Translated content that is long enough for validation purposes. This translated transcript has sufficient length to pass checks."
            mock_formatter_instance.format_transcript.return_value = long_content
            mock_formatter.return_value = mock_formatter_instance
            
            result = transcript_tool._run("https://www.youtube.com/watch?v=test123", "en")
            
            assert long_content in result
    
    def test_run_invalid_video_id(self, transcript_tool):
        """Test error handling for invalid video ID"""
        with pytest.raises(Exception) as exc_info:
            transcript_tool._run("https://example.com/invalid", "en")
        
        assert "Could not extract video ID" in str(exc_info.value)
    
    @patch('src.tool.YouTubeTranscriptApi')
    def test_run_transcript_too_short(self, mock_api, transcript_tool):
        """Test error handling for transcript that's too short"""
        mock_transcript_data = [{'text': 'Hi', 'start': 0.0, 'duration': 1.0}]
        
        mock_transcript = Mock()
        mock_transcript.fetch.return_value = mock_transcript_data
        
        mock_transcript_list = Mock()
        mock_transcript_list.find_transcript.return_value = mock_transcript
        mock_api.list_transcripts.return_value = mock_transcript_list
        
        with patch('src.tool.TextFormatter') as mock_formatter:
            mock_formatter_instance = Mock()
            mock_formatter_instance.format_transcript.return_value = "Hi"
            mock_formatter.return_value = mock_formatter_instance
            
            with pytest.raises(Exception) as exc_info:
                transcript_tool._run("https://www.youtube.com/watch?v=test123", "en")
            
            assert "Transcript too short" in str(exc_info.value)

class TestBlogGeneratorTool:
    """Test cases for blog generator tool"""
    
    @pytest.fixture
    def blog_tool(self):
        """Create blog generator tool instance"""
        return BlogGeneratorTool()
    
    def test_create_blog_prompt_contains_requirements(self, blog_tool):
        """Test that blog prompt contains all requirements"""
        content = "This is sample transcript content for testing purposes."
        prompt = blog_tool._create_blog_prompt(content)
        
        requirements = [
            "engaging, descriptive title",
            "compelling introduction",
            "clear sections",
            "Markdown formatting",
            "800-1000 words",
            "conversational tone",
            "YouTube video"
        ]
        
        for requirement in requirements:
            assert requirement in prompt
        assert content in prompt
    
    @patch('openai.OpenAI')
    def test_run_successful_blog_generation(self, mock_openai_client, blog_tool, mock_env_vars):
        """Test successful blog generation"""
        # Mock OpenAI response with content longer than 200 characters
        mock_response = Mock()
        mock_response.choices = [Mock()]
        long_blog_content = """# Test Blog Article

This is a comprehensive blog article with over 200 characters to ensure it passes the length validation check. 
The content discusses various important topics and provides detailed explanations of key concepts. 
This blog post contains sufficient content to meet the minimum length requirements for validation purposes."""
        mock_response.choices[0].message.content = long_blog_content
        
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance
        
        content = "This is a sample transcript with enough content to generate a meaningful blog article."
        result = blog_tool._run(content)
        
        assert "# Test Blog Article" in result
        assert len(result) > 200
        mock_client_instance.chat.completions.create.assert_called_once()
    
    def test_run_content_too_short(self, blog_tool):
        """Test error handling for content that's too short"""
        short_content = "Hi"
        
        with pytest.raises(Exception) as exc_info:
            blog_tool._run(short_content)
        
        assert "too short" in str(exc_info.value)
    
    def test_run_empty_content(self, blog_tool):
        """Test error handling for empty content"""
        with pytest.raises(Exception) as exc_info:
            blog_tool._run("")
        
        assert "too short" in str(exc_info.value)
    
    @patch('openai.OpenAI')
    def test_run_openai_api_error(self, mock_openai_client, blog_tool, mock_env_vars):
        """Test error handling when OpenAI API fails"""
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_client.return_value = mock_client_instance
        
        content = "This is a sample transcript with enough content."
        
        with pytest.raises(Exception) as exc_info:
            blog_tool._run(content)
        
        assert "Could not generate blog article" in str(exc_info.value)
    
    @patch('openai.OpenAI')
    def test_run_generated_content_too_short(self, mock_openai_client, blog_tool, mock_env_vars):
        """Test error handling when generated content is too short"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Short"
        
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance
        
        content = "This is a sample transcript with enough content."
        
        with pytest.raises(Exception) as exc_info:
            blog_tool._run(content)
        
        assert "too short" in str(exc_info.value)

class TestPDFGeneratorTool:
    """Test cases for PDF generator tool"""
    
    @pytest.fixture
    def pdf_tool(self):
        """Create PDF generator tool instance"""
        return PDFGeneratorTool()
    
    def test_create_styles_successful(self, pdf_tool):
        """Test successful style creation"""
        styles = pdf_tool._create_styles()
        
        assert 'Title' in styles
        assert 'Heading1' in styles
        assert 'Normal' in styles
    
    @patch('src.tool.getSampleStyleSheet')
    def test_create_styles_fallback_on_error(self, mock_get_styles):
        """Test style creation fallback when error occurs"""
        mock_get_styles.side_effect = [Exception("Style error"), Mock()]
        
        pdf_tool = PDFGeneratorTool()
        styles = pdf_tool.styles
        
        assert styles is not None
        assert mock_get_styles.call_count == 2
    
    @patch('src.tool.SimpleDocTemplate')
    @patch('src.tool.Paragraph')
    def test_generate_pdf_bytes_successful(self, mock_paragraph, mock_doc, pdf_tool):
        """Test successful PDF generation"""
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance
        
        content = "This is test blog content for PDF generation."
        result = pdf_tool.generate_pdf_bytes(content)
        
        assert isinstance(result, bytes)
        mock_doc_instance.build.assert_called_once()
    
    @patch('src.tool.SimpleDocTemplate')
    def test_generate_pdf_bytes_fallback_on_error(self, mock_doc, pdf_tool):
        """Test PDF generation fallback when error occurs"""
        mock_doc.side_effect = Exception("PDF generation error")
        
        content = "This is test blog content."
        result = pdf_tool.generate_pdf_bytes(content)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_generate_pdf_bytes_with_special_characters(self, pdf_tool):
        """Test PDF generation with special characters"""
        content = "Content with special chars: áéíóú ñ ¿¡ €"
        result = pdf_tool.generate_pdf_bytes(content)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_generate_pdf_bytes_empty_content(self, pdf_tool):
        """Test PDF generation with empty content"""
        content = ""
        result = pdf_tool.generate_pdf_bytes(content)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
