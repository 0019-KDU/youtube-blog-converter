import pytest
from unittest.mock import patch, MagicMock, Mock, mock_open
import requests
import json
import re
import os
import io
from pathlib import Path
from fpdf import FPDF
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFGeneratorTool

# Test fixtures and setup
@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'SUPADATA_API_KEY': 'test_supadata_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'OPENAI_MODEL_NAME': 'gpt-4.1-nano-2025-04-14'
    }, clear=True):
        with patch('src.tool.SUPADATA_API_KEY', 'test_supadata_key'):
            with patch('src.tool.OPENAI_API_KEY', 'test_openai_key'):
                yield

@pytest.fixture
def clear_env_vars():
    """Clear all environment variables for testing"""
    with patch.dict(os.environ, {}, clear=True):
        with patch('src.tool.SUPADATA_API_KEY', None):
            with patch('src.tool.OPENAI_API_KEY', None):
                with patch('src.tool.openai_client', None):
                    yield

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    with patch('src.tool.openai_client') as mock_client:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='Generated blog content'))]
        mock_client.chat.completions.create.return_value = mock_response
        yield mock_client

@pytest.fixture
def sample_transcript():
    """Sample transcript for testing"""
    return "This is a sample YouTube transcript with technical content about AI tools and frameworks. " * 10

@pytest.fixture
def sample_blog_content():
    """Sample blog content for testing"""
    return """# AI Tools Review

## Introduction
This comprehensive review covers the latest AI tools and frameworks.

## Main Tools
- **Tool 1**: Advanced AI framework
- **Tool 2**: Machine learning platform

### Technical Specifications
1. Performance metrics
2. Integration capabilities
3. Scalability features

## Conclusion
These tools represent the current state of AI technology."""

class TestYouTubeTranscriptTool:
    """Test cases for YouTubeTranscriptTool class"""
    
    def test_init_success(self, mock_env_vars):
        """Test successful initialization with API key"""
        tool = YouTubeTranscriptTool()
        assert tool is not None
    
    def test_init_missing_api_key(self, clear_env_vars):
        """Test initialization failure when API key is missing"""
        with patch('src.tool.SUPADATA_API_KEY', None):
            with pytest.raises(RuntimeError, match="Supadata API key not configured"):
                YouTubeTranscriptTool()
    
    @patch('requests.get')
    def test_run_success(self, mock_get, mock_env_vars):
        """Test successful transcript extraction"""
        with patch('src.tool.SUPADATA_API_KEY', 'test_supadata_key'):
            mock_response = MagicMock()
            mock_response.json.return_value = {'content': 'Sample transcript content'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            tool = YouTubeTranscriptTool()
            result = tool._run('https://youtube.com/watch?v=test123', 'en')
            
            assert result == 'Sample transcript content'
            mock_get.assert_called_once()
            
            # Verify correct API call parameters
            call_args = mock_get.call_args
            assert call_args[1]['params']['url'] == 'https://youtube.com/watch?v=test123'
            assert call_args[1]['params']['lang'] == 'en'
            assert call_args[1]['params']['text'] == 'true'
            assert call_args[1]['headers']['x-api-key'] == 'test_supadata_key'
    
    @patch('requests.get')
    def test_run_no_content(self, mock_get, mock_env_vars):
        """Test when transcript content is not found"""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=invalid', 'en')
        
        assert result.startswith('ERROR: Transcript not found')
        assert 'https://youtube.com/watch?v=invalid' in result
    
    @patch('requests.get')
    def test_run_http_error(self, mock_get, mock_env_vars):
        """Test HTTP error handling"""
        mock_get.side_effect = requests.exceptions.HTTPError('404 Not Found')
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=error', 'en')
        
        assert result.startswith('ERROR: HTTP error')
        assert '404 Not Found' in result
    
    @patch('requests.get')
    def test_run_request_exception(self, mock_get, mock_env_vars):
        """Test request exception handling"""
        mock_get.side_effect = requests.exceptions.RequestException('Connection error')
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=error', 'en')
        
        assert result.startswith('ERROR: Request failed')
        assert 'Connection error' in result
    
    @patch('requests.get')
    def test_run_json_decode_error(self, mock_get, mock_env_vars):
        """Test JSON decode error handling"""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=error', 'en')
        
        assert result.startswith('ERROR: Invalid response')
    
    @patch('requests.get')
    def test_run_unexpected_error(self, mock_get, mock_env_vars):
        """Test unexpected error handling"""
        mock_get.side_effect = Exception('Unexpected error')
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=error', 'en')
        
        assert result.startswith('ERROR: Unexpected error')
        assert 'Unexpected error' in result
    
    @patch('requests.get')
    def test_run_with_different_language(self, mock_get, mock_env_vars):
        """Test with different language parameter"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'content': 'Spanish transcript'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        tool = YouTubeTranscriptTool()
        result = tool._run('https://youtube.com/watch?v=test123', 'es')
        
        assert result == 'Spanish transcript'
        # Verify correct language parameter was passed
        call_args = mock_get.call_args
        assert call_args[1]['params']['lang'] == 'es'

class TestBlogGeneratorTool:
    """Test cases for BlogGeneratorTool class"""
    
    def test_init_success(self, mock_env_vars, mock_openai_client):
        """Test successful initialization"""
        tool = BlogGeneratorTool()
        assert tool is not None
    
    def test_init_missing_api_key(self, clear_env_vars):
        """Test initialization failure when OpenAI API key is missing"""
        with patch('src.tool.OPENAI_API_KEY', None):
            with patch('src.tool.openai_client', None):
                with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
                    BlogGeneratorTool()
    
    def test_init_missing_openai_client(self, mock_env_vars):
        """Test initialization failure when OpenAI client is None"""
        with patch('src.tool.openai_client', None):
            with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
                BlogGeneratorTool()
    
    def test_run_empty_transcript(self, mock_env_vars, mock_openai_client):
        """Test with empty transcript"""
        tool = BlogGeneratorTool()
        result = tool._run('')
        
        assert result == 'ERROR: Invalid or empty transcript provided'
    
    def test_run_short_transcript(self, mock_env_vars, mock_openai_client):
        """Test with transcript shorter than 100 characters"""
        tool = BlogGeneratorTool()
        result = tool._run('Short text')
        
        assert result == 'ERROR: Invalid or empty transcript provided'
    
    def test_run_error_transcript(self, mock_env_vars, mock_openai_client):
        """Test with error transcript"""
        tool = BlogGeneratorTool()
        # Use a longer error message to pass the length check
        long_error = "ERROR: Some error occurred " + "x" * 100
        result = tool._run(long_error)
        
        assert result.startswith('ERROR:')
        assert 'Some error occurred' in result
    
    def test_run_success(self, mock_env_vars, mock_openai_client, sample_transcript):
        """Test successful blog generation"""
        tool = BlogGeneratorTool()
        result = tool._run(sample_transcript)
        
        assert len(result) > 0
        assert not result.startswith('ERROR:')
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify API call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4.1-nano-2025-04-14'
        assert call_args[1]['temperature'] == 0.2
        assert call_args[1]['max_tokens'] == 5000
    
    def test_run_openai_error(self, mock_env_vars, mock_openai_client, sample_transcript):
        """Test OpenAI API error handling"""
        mock_openai_client.chat.completions.create.side_effect = Exception('OpenAI API error')
        
        tool = BlogGeneratorTool()
        result = tool._run(sample_transcript)
        
        assert result.startswith('ERROR: Blog generation failed')
        assert 'OpenAI API error' in result
    
    def test_run_with_long_transcript(self, mock_env_vars, mock_openai_client):
        """Test with very long transcript (truncation)"""
        long_transcript = "A" * 20000  # Longer than 15000 char limit
        
        tool = BlogGeneratorTool()
        result = tool._run(long_transcript)
        
        # Verify the call was made with truncated content
        call_args = mock_openai_client.chat.completions.create.call_args
        prompt_content = call_args[1]['messages'][1]['content']
        assert len(prompt_content) < 20000
        assert 'A' * 15000 in prompt_content
    
    def test_clean_markdown_content_empty(self, mock_env_vars, mock_openai_client):
        """Test cleaning empty content"""
        tool = BlogGeneratorTool()
        result = tool._clean_markdown_content('')
        
        assert result == ''
    
    def test_clean_markdown_content_artifacts(self, mock_env_vars, mock_openai_client):
        """Test cleaning markdown artifacts"""
        content = """**Bold text** *italic text* 
        ___underscores___
        ---horizontal rule---
        ||pipes||
        ``````
        `inline code`
        #### Too many hashes
        * asterisk list
        1. numbered list"""
        
        tool = BlogGeneratorTool()
        result = tool._clean_markdown_content(content)
        
        # Check that artifacts are removed
        assert '**' not in result
        assert '*italic text*' not in result
        assert '___' not in result
        assert '---' not in result
        assert '||' not in result
        assert '```' not in result
        assert '`' not in result
        assert '####' not in result
        # Check that list formatting is fixed
        assert '- asterisk list' in result
        assert '1. numbered list' in result
    
    def test_clean_markdown_content_spacing(self, mock_env_vars, mock_openai_client):
        """Test spacing and formatting fixes"""
        content = """# Title


## Section


Paragraph with   trailing spaces   


- List item
"""
        
        tool = BlogGeneratorTool()
        result = tool._clean_markdown_content(content)
        
        # Check proper spacing
        assert '\n\n\n' not in result
        assert result.count('\n\n') <= result.count('\n') // 2
    
    def test_clean_markdown_content_headings(self, mock_env_vars, mock_openai_client):
        """Test heading formatting"""
        content = """#Title without space
##   Section with extra spaces   
##### Too many hashes
"""
        
        tool = BlogGeneratorTool()
        result = tool._clean_markdown_content(content)
        
        # Check proper heading format
        assert '# Title without space' in result
        assert '## Section with extra spaces' in result
        assert '### Too many hashes' in result

class TestPDFGeneratorTool:
    """Test cases for PDFGeneratorTool class"""
    
    def test_init_success(self):
        """Test successful initialization"""
        tool = PDFGeneratorTool()
        assert tool is not None
    
    def test_clean_unicode_text_empty(self):
        """Test cleaning empty text"""
        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text('')
        
        assert result == ''
    
    def test_clean_unicode_text_replacements(self):
        """Test Unicode character replacements"""
        text = "Text with — em dash – en dash ' quotes \" and … ellipsis • bullet"
        
        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text(text)
        
        # Check replacements
        assert '--' in result  # em dash
        assert '-' in result   # en dash
        assert "'" in result   # single quotes
        assert '"' in result   # double quotes
        assert '...' in result # ellipsis
        assert '*' in result   # bullet point (now using actual bullet Unicode: •)


    
    def test_clean_unicode_text_arrows(self):
        """Test arrow character replacements"""
        text = 'Arrows: ← → ↑ ↓ and math: × ÷ − symbols'
        
        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text(text)
        
        assert '<-' in result  # left arrow
        assert '->' in result  # right arrow
        assert '^' in result   # up arrow
        assert 'v' in result   # down arrow
        assert 'x' in result   # multiplication
        assert '/' in result   # division
        assert '-' in result   # minus
    
    def test_clean_unicode_text_non_ascii_removal(self):
        """Test removal of non-ASCII characters"""
        text = 'Hello 世界 World ñ café'
        
        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text(text)
        
        # Check that non-ASCII characters are replaced with '?'
        assert '?' in result
        assert '世' not in result
        assert '界' not in result
        assert 'ñ' not in result
    
    def test_clean_unicode_text_ascii_preserved(self):
        """Test that ASCII characters are preserved"""
        text = 'Hello World 123 !@#$%^&*()'
        
        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text(text)
        
        assert result == text  # Should remain unchanged
    
    def test_generate_pdf_bytes_simple_content(self, sample_blog_content):
        """Test PDF generation with simple content"""
        tool = PDFGeneratorTool()
        pdf_bytes = tool.generate_pdf_bytes(sample_blog_content)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')  # PDF header
    
    def test_generate_pdf_bytes_empty_content(self):
        """Test PDF generation with empty content"""
        tool = PDFGeneratorTool()
        pdf_bytes = tool.generate_pdf_bytes('')
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_pdf_bytes_unicode_content(self):
        """Test PDF generation with Unicode content"""
        content = """# Title with — special chars
        
## Section with -  bullets and … ellipsis

Content with various Unicode: ← → ↑ ↓ characters."""
        
        tool = PDFGeneratorTool()
        pdf_bytes = tool.generate_pdf_bytes(content)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_pdf_bytes_different_content_types(self):
        """Test PDF generation with different content structures"""
        content = """# Main Title

## Section 1
Regular paragraph text.

### Subsection
More text here.

## Lists Section
- Bullet point 1
- Bullet point 2
- Bullet point 3

1. Numbered item 1
2. Numbered item 2
3. Numbered item 3

## Final Section
Final paragraph content."""
        
        tool = PDFGeneratorTool()
        pdf_bytes = tool.generate_pdf_bytes(content)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_generate_pdf_bytes_no_title(self):
        """Test PDF generation without main title"""
        content = """## Section without main title
        
Content without a main # heading."""
        
        tool = PDFGeneratorTool()
        pdf_bytes = tool.generate_pdf_bytes(content)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    @patch('fpdf.FPDF.output')
    def test_generate_pdf_bytes_fpdf_error(self, mock_output):
        """Test PDF generation with FPDF error"""
        mock_output.side_effect = Exception('PDF generation failed')
        
        tool = PDFGeneratorTool()
        
        with pytest.raises(RuntimeError, match="PDF generation error"):
            tool.generate_pdf_bytes("Test content")
    
    @patch('fpdf.FPDF.output')
    def test_generate_pdf_bytes_different_return_types(self, mock_output):
        """Test handling different return types from FPDF"""
        tool = PDFGeneratorTool()
        
        # Test bytes return
        mock_output.return_value = b'PDF content'
        result = tool.generate_pdf_bytes("Test")
        assert isinstance(result, bytes)
        
        # Test bytearray return
        mock_output.return_value = bytearray(b'PDF content')
        result = tool.generate_pdf_bytes("Test")
        assert isinstance(result, bytes)
        
        # Test string return
        mock_output.return_value = 'PDF content'
        result = tool.generate_pdf_bytes("Test")
        assert isinstance(result, bytes)
    
    def test_generate_pdf_bytes_long_content(self):
        """Test PDF generation with very long content"""
        long_content = "# Long Content Test\n\n" + "This is a very long paragraph. " * 1000
        
        tool = PDFGeneratorTool()
        pdf_bytes = tool.generate_pdf_bytes(long_content)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

# Integration tests
class TestIntegration:
    """Integration tests for tool interactions"""
    
    @patch('requests.get')
    def test_transcript_to_blog_workflow(self, mock_get, mock_env_vars, mock_openai_client):
        """Test complete workflow from transcript to blog"""
        # Mock transcript response
        mock_response = MagicMock()
        mock_response.json.return_value = {'content': 'Sample transcript for blog generation' * 10}  # Make it long enough
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test transcript tool
        transcript_tool = YouTubeTranscriptTool()
        transcript = transcript_tool._run('https://youtube.com/watch?v=test123', 'en')
        
        # Test blog generator tool
        blog_tool = BlogGeneratorTool()
        blog_content = blog_tool._run(transcript)
        
        # Test PDF generator tool
        pdf_tool = PDFGeneratorTool()
        pdf_bytes = pdf_tool.generate_pdf_bytes(blog_content)
        
        # Updated assertions
        assert transcript == 'Sample transcript for blog generation' * 10
        assert not blog_content.startswith('ERROR:')
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
    
    def test_error_propagation(self, mock_env_vars, mock_openai_client):
        """Test error propagation through workflow"""
        # Start with error transcript
        error_transcript = "ERROR: Failed to extract transcript"
        
        # Test blog generator with error input
        blog_tool = BlogGeneratorTool()
        blog_result = blog_tool._run(error_transcript)
        
        assert blog_result.startswith('ERROR:')
        
        # Test PDF generator with error content
        pdf_tool = PDFGeneratorTool()
        pdf_bytes = pdf_tool.generate_pdf_bytes(blog_result)
        
        # PDF should still be generated even with error content
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

# Test configuration and utilities
class TestEnvironmentHandling:
    """Test environment variable handling"""
    
    def test_missing_supadata_key_environment(self):
        """Test behavior when SUPADATA_API_KEY is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.tool.SUPADATA_API_KEY', None):
                with pytest.raises(RuntimeError):
                    YouTubeTranscriptTool()
    
    def test_missing_openai_key_environment(self):
        """Test behavior when OPENAI_API_KEY is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.tool.OPENAI_API_KEY', None):
                with patch('src.tool.openai_client', None):
                    with pytest.raises(RuntimeError):
                        BlogGeneratorTool()
    
    def test_partial_environment_setup(self):
        """Test with partial environment configuration"""
        with patch.dict(os.environ, {'SUPADATA_API_KEY': 'test_key'}, clear=True):
            with patch('src.tool.SUPADATA_API_KEY', 'test_key'):
                # This should work
                tool = YouTubeTranscriptTool()
                assert tool is not None
                
                # This should fail
                with patch('src.tool.OPENAI_API_KEY', None):
                    with patch('src.tool.openai_client', None):
                        with pytest.raises(RuntimeError):
                            BlogGeneratorTool()

# Performance and edge case tests
class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_url(self, mock_env_vars):
        """Test with very long URL"""
        long_url = "https://youtube.com/watch?v=test123&" + "param=value&" * 1000
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {'content': 'Content'}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            tool = YouTubeTranscriptTool()
            result = tool._run(long_url, 'en')
            
            assert result == 'Content'
    
    def test_special_characters_in_content(self, mock_env_vars, mock_openai_client):
        """Test handling of special characters"""
        special_content = "Content with special chars: <>&\"'`~!@#$%^&*()[]{}|\\:;\"'<>,.?/" * 10
        
        tool = BlogGeneratorTool()
        result = tool._run(special_content)
        
        assert not result.startswith('ERROR:')
    
