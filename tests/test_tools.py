from json import tool
import unittest
import unittest.mock as mock
from unittest.mock import patch, MagicMock, call
import hashlib
import time
import io
import os
import re
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import your modules (adjust the import path as needed)
from src.tool import (
    YouTubeTranscriptTool, 
    BlogGeneratorTool, 
    PDFGeneratorTool, 
    get_env_var,
    TranscriptInput,
    BlogInput
)


class TestYouTubeTranscriptTool(unittest.TestCase):
    """Comprehensive test suite for YouTubeTranscriptTool"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = YouTubeTranscriptTool()
        self.valid_youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.invalid_youtube_url = "https://invalid-url.com"
        self.sample_transcript_data = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 2.0},
            {'text': 'This is a test', 'start': 2.0, 'duration': 3.0},
            {'text': 'Docker wins the container race', 'start': 5.0, 'duration': 4.0}
        ]

    def test_init_resets_tool_state(self):
        """Test that initialization properly resets tool state"""
        self.assertIsNone(self.tool._last_input_hash)
        self.assertEqual(self.tool._call_count, 0)
        self.assertIsNotNone(self.tool._session_id)
        self.assertEqual(self.tool._last_call_time, 0)

    def test_reset_tool_state(self):
        """Test _reset_tool_state method"""
        # Set some state
        self.tool._last_input_hash = "test_hash"
        self.tool._call_count = 5
        self.tool._last_call_time = 12345
        
        # Reset and verify
        self.tool._reset_tool_state()
        self.assertIsNone(self.tool._last_input_hash)
        self.assertEqual(self.tool._call_count, 0)
        self.assertEqual(self.tool._last_call_time, 0)

    def test_extract_video_id_valid_urls(self):
        """Test video ID extraction from various YouTube URL formats"""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ")
        ]
        
        for url, expected_id in test_cases:
            with self.subTest(url=url):
                result = self.tool._extract_video_id(url)
                self.assertEqual(result, expected_id)

    def test_extract_video_id_invalid_urls(self):
        """Test video ID extraction with invalid URLs"""
        invalid_urls = [
            "",
            None,
            "https://invalid-url.com",
            "https://www.youtube.com/watch?v=invalid",
            "not-a-url",
            "https://youtube.com/watch?v=toolong12345",
            "https://youtube.com/watch?v=short"
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                result = self.tool._extract_video_id(url)
                self.assertIsNone(result)

    def test_enhanced_clean_transcript_empty_input(self):
        """Test transcript cleaning with empty input"""
        result = self.tool._enhanced_clean_transcript("")
        self.assertEqual(result, "")

    def test_enhanced_clean_transcript_with_artifacts(self):
        """Test transcript cleaning removes artifacts"""
        transcript = "Hello [Music] world [Applause] test [Laughter] content [Silence]"
        result = self.tool._enhanced_clean_transcript(transcript)
        self.assertNotIn("[Music]", result)
        self.assertNotIn("[Applause]", result)
        self.assertNotIn("[Laughter]", result)
        self.assertNotIn("[Silence]", result)
        self.assertIn("Hello", result)
        self.assertIn("world", result)

    def test_enhanced_clean_transcript_preserves_technical_terms(self):
        """Test that technical terms are preserved during cleaning"""
        transcript = "Docker wins the container category. Kubernetes vs Docker comparison."
        result = self.tool._enhanced_clean_transcript(transcript)
        self.assertIn("Docker", result)
        self.assertIn("Kubernetes", result)
        self.assertIn("wins", result)

    def test_enhanced_clean_transcript_cleans_punctuation(self):
        """Test that excessive punctuation is cleaned"""
        transcript = "Hello... world??? Test!!! More content.."
        result = self.tool._enhanced_clean_transcript(transcript)
        self.assertNotIn("...", result)
        self.assertNotIn("???", result)
        self.assertNotIn("!!!", result)

    @patch('src.tool.YouTubeTranscriptApi.list_transcripts')
    def test_process_transcript_success(self, mock_list_transcripts):
        """Test successful transcript processing"""
        mock_transcript = MagicMock()
        mock_transcript.fetch.return_value = self.sample_transcript_data

        with patch('src.tool.TextFormatter') as mock_formatter:
            mock_formatter_instance = MagicMock()
            mock_formatter.return_value = mock_formatter_instance
            mock_formatter_instance.format_transcript.return_value = "Formatted transcript"
            
            result = self.tool._process_transcript(mock_transcript)
            self.assertEqual(result, "Formatted transcript")
            mock_transcript.fetch.assert_called_once()

    @patch('src.tool.YouTubeTranscriptApi.list_transcripts')
    def test_process_transcript_failure(self, mock_list_transcripts):
        """Test transcript processing failure"""
        mock_transcript = MagicMock()
        mock_transcript.fetch.side_effect = Exception("Fetch failed")
        
        with self.assertRaises(Exception):
            self.tool._process_transcript(mock_transcript)

    @patch('src.tool.YouTubeTranscriptApi.list_transcripts')
    @patch('src.tool.time.sleep')
    def test_get_transcript_with_fallbacks_english(self, mock_sleep, mock_list_transcripts):
        """Test transcript retrieval with English fallback"""
        mock_transcript_list = MagicMock()
        mock_list_transcripts.return_value = mock_transcript_list
        
        mock_transcript = MagicMock()
        mock_transcript_list.find_transcript.return_value = mock_transcript
        
        with patch.object(self.tool, '_process_transcript', return_value="Test transcript"):
            result = self.tool._get_transcript_with_fallbacks("test_id", "en")
            self.assertEqual(result, "Test transcript")

    @patch('src.tool.YouTubeTranscriptApi.list_transcripts')
    def test_get_transcript_with_fallbacks_translation(self, mock_list_transcripts):
        """Test transcript retrieval with translation fallback"""
        mock_transcript_list = MagicMock()
        mock_list_transcripts.return_value = mock_transcript_list
        
        # First call fails (no English), second call succeeds with translation
        mock_transcript_list.find_transcript.side_effect = [Exception("No English"), None]
        mock_transcript_list.find_generated_transcript.side_effect = Exception("No auto-generated")
        
        # Mock available transcripts
        mock_available_transcript = MagicMock()
        mock_available_transcript.language_code = "es"
        mock_translated = MagicMock()
        mock_available_transcript.translate.return_value = mock_translated
        mock_transcript_list.__iter__.return_value = [mock_available_transcript]
        
        with patch.object(self.tool, '_process_transcript', return_value="Translated transcript"):
            result = self.tool._get_transcript_with_fallbacks("test_id", "en")
            self.assertEqual(result, "Translated transcript")

    @patch('src.tool.YouTubeTranscriptApi.list_transcripts')
    def test_get_transcript_with_fallbacks_no_transcripts(self, mock_list_transcripts):
        """Test transcript retrieval when no transcripts available"""
        mock_list_transcripts.side_effect = Exception("No transcripts")
        
        with self.assertRaises(Exception):
            self.tool._get_transcript_with_fallbacks("test_id", "en")

    @patch('src.tool.time.sleep')
    @patch.object(YouTubeTranscriptTool, '_get_transcript_with_fallbacks')
    @patch.object(YouTubeTranscriptTool, '_extract_video_id')
    def test_run_successful_extraction(self, mock_extract_id, mock_get_transcript, mock_sleep):
        """Test successful transcript extraction"""
        mock_extract_id.return_value = "test_video_id"
        mock_get_transcript.return_value = "This is a long enough transcript content for testing purposes."
        
        result = self.tool._run(self.valid_youtube_url, "en")
        self.assertNotIn("ERROR:", result)
        self.assertGreater(len(result), 0)

    def test_run_with_invalid_url(self):
        """Test _run method with invalid YouTube URL"""
        result = self.tool._run(self.invalid_youtube_url, "en")
        self.assertIn("ERROR:", result)
        self.assertIn("Could not extract video ID", result)

    @patch.object(YouTubeTranscriptTool, '_extract_video_id')
    def test_run_with_extraction_exception(self, mock_extract_id):
        """Test _run method when video ID extraction fails"""
        mock_extract_id.return_value = None
        
        result = self.tool._run(self.valid_youtube_url, "en")
        self.assertIn("ERROR:", result)

    @patch.object(YouTubeTranscriptTool, '_extract_video_id')
    @patch.object(YouTubeTranscriptTool, '_get_transcript_with_fallbacks')
    def test_run_with_short_transcript(self, mock_get_transcript, mock_extract_id):
        """Test _run method with transcript too short"""
        mock_extract_id.return_value = "test_id"
        mock_get_transcript.return_value = "short"
        
        result = self.tool._run(self.valid_youtube_url, "en")
        self.assertIn("ERROR:", result)
        self.assertIn("Transcript too short", result)

    @patch('src.tool.time.time')
    @patch('src.tool.time.sleep')
    @patch.object(YouTubeTranscriptTool, '_get_transcript_with_fallbacks')
    @patch.object(YouTubeTranscriptTool, '_extract_video_id')
    def test_run_input_reuse_detection(self, mock_extract_id, mock_get_transcript, mock_sleep, mock_time):
        """Test input reuse detection and variation"""
        mock_extract_id.return_value = "test_id"
        mock_get_transcript.return_value = "This is a long enough transcript content for testing purposes."
        mock_time.side_effect = [1000.0, 1000.5, 1001.0, 1003.0]  # Simulate time progression
        
        # First call
        result1 = self.tool._run(self.valid_youtube_url, "en")
        self.assertNotIn("ERROR:", result1)
        
        # Second call (should detect reuse)
        result2 = self.tool._run(self.valid_youtube_url, "en")
        self.assertNotIn("ERROR:", result2)
        
        # Verify sleep was called for reuse detection
        mock_sleep.assert_called()


class TestBlogGeneratorTool(unittest.TestCase):
    """Comprehensive test suite for BlogGeneratorTool"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = BlogGeneratorTool()
        self.sample_content = "This is a sample transcript content for testing purposes. " * 20
        self.short_content = "Short content"

    def test_init_resets_tool_state(self):
        """Test initialization resets tool state"""
        self.assertIsNone(self.tool._last_input_hash)
        self.assertEqual(self.tool._generation_count, 0)

    def test_reset_tool_state(self):
        """Test _reset_tool_state method"""
        self.tool._last_input_hash = "test_hash"
        self.tool._generation_count = 2
        
        self.tool._reset_tool_state()
        self.assertIsNone(self.tool._last_input_hash)
        self.assertEqual(self.tool._generation_count, 0)

    def test_extract_content_from_context_various_sources(self):
        """Test content extraction from various context sources"""
        test_cases = [
            {'context': self.sample_content},
            {'transcript': self.sample_content},
            {'input': self.sample_content},
            {'text': self.sample_content},
            {'custom_key': self.sample_content}
        ]
        
        for kwargs in test_cases:
            with self.subTest(kwargs=kwargs):
                result = self.tool._extract_content_from_context(**kwargs)
                self.assertEqual(result, self.sample_content)

    def test_extract_content_from_context_no_valid_content(self):
        """Test content extraction when no valid content is available"""
        result = self.tool._extract_content_from_context(short="hi", empty="", none_val=None)
        self.assertIsNone(result)

    def test_extract_content_from_context_short_content(self):
        """Test content extraction with content too short"""
        result = self.tool._extract_content_from_context(content="short")
        self.assertIsNone(result)

    def test_extract_key_information_tools(self):
        """Test key information extraction - tools"""
        content = "Docker wins the container race. Kubernetes vs Docker comparison. Fabric API is great."
        result = self.tool._extract_key_information(content)
        
        self.assertIn('tools', result)
        self.assertIn('Docker', result['tools'])
        self.assertIn('Kubernetes', result['tools'])
        self.assertIn('Fabric', result['tools'])

    def test_extract_key_information_winners(self):
        """Test key information extraction - winners"""
        content = "Docker wins the race. Kubernetes is the winner. Helm is a clear choice."
        result = self.tool._extract_key_information(content)
        
        self.assertIn('winners', result)
        self.assertTrue(len(result['winners']) > 0)

    def test_extract_key_information_comparisons(self):
        """Test key information extraction - comparisons"""
        content = "Docker vs Kubernetes comparison. React versus Angular framework."
        result = self.tool._extract_key_information(content)
        
        self.assertIn('comparisons', result)
        self.assertTrue(any('vs' in comp for comp in result['comparisons']))

    def test_extract_key_information_versions(self):
        """Test key information extraction - versions"""
        content = "Version 1.2.3 was released. Updated to version 2.0.1."
        result = self.tool._extract_key_information(content)
        
        self.assertIn('versions', result)
        self.assertIn('1.2.3', result['versions'])
        self.assertIn('2.0.1', result['versions'])

    def test_extract_key_information_categories(self):
        """Test key information extraction - categories"""
        content = "Container category tools. Database area solutions. Security field options."
        result = self.tool._extract_key_information(content)
        
        self.assertIn('categories', result)
        self.assertTrue(len(result['categories']) > 0)

    def test_get_detail_preserving_system_prompt(self):
        """Test system prompt generation"""
        prompt = self.tool._get_detail_preserving_system_prompt()
        self.assertIsInstance(prompt, str)
        self.assertIn("PRESERVE", prompt)
        self.assertIn("technical", prompt)
        self.assertGreater(len(prompt), 500)

    def test_create_detail_preserving_prompt_normal_length(self):
        """Test prompt creation with normal length content"""
        key_info = {
            'tools': ['Docker', 'Kubernetes'],
            'winners': ['Docker'],
            'categories': ['Container'],
            'comparisons': ['Docker vs Kubernetes'],
            'versions': ['1.0']
        }
        
        result = self.tool._create_detail_preserving_prompt(self.sample_content, key_info)
        self.assertIn("Docker", result)
        self.assertIn("Kubernetes", result)
        self.assertIn("PRESERVE", result)

    def test_create_detail_preserving_prompt_long_content(self):
        """Test prompt creation with content that needs truncation"""
        long_content = "Docker is great. " * 1000  # Create very long content
        key_info = {
            'tools': ['Docker'],
            'winners': [],
            'categories': [],
            'comparisons': [],
            'versions': []
        }
        
        result = self.tool._create_detail_preserving_prompt(long_content, key_info)
        self.assertIn("Docker", result)
        self.assertIn("truncated", result.lower())

    def test_preserve_details_clean_content_removes_tool_references(self):
        """Test content cleaning removes tool references"""
        content = "Action: BlogGeneratorTool\nTechnical content here\nTool: BlogGeneratorTool"
        result = self.tool._preserve_details_clean_content(content)
        self.assertNotIn("BlogGeneratorTool", result)
        self.assertIn("Technical content", result)

    def test_preserve_details_clean_content_removes_json(self):
        """Test content cleaning removes JSON artifacts"""
        content = '{"key": "value"}\nActual content here\n{"another": "json"}'
        result = self.tool._preserve_details_clean_content(content)
        self.assertNotIn('{"key":', result)
        self.assertIn("Actual content", result)

    def test_preserve_details_clean_content_fixes_formatting(self):
        """Test content cleaning fixes formatting issues"""
        content = "Title\n\n\n\nContent here\n\n\n\nMore content"
        result = self.tool._preserve_details_clean_content(content)
        self.assertNotIn("\n\n\n", result)

    def test_validate_content_specificity(self):
        """Test content specificity validation"""
        result = self.tool._validate_content_specificity("any content", {})
        self.assertTrue(result)  # Always returns True as per implementation

    def test_run_no_content_provided(self):
        """Test _run method with no content"""
        result = self.tool._run()
        self.assertIn("ERROR:", result)
        self.assertIn("No transcript content provided", result)

    def test_run_content_too_short(self):
        """Test _run method with content too short"""
        result = self.tool._run(content=self.short_content)
        self.assertIn("ERROR:", result)
        self.assertIn("No transcript content provided", result)

    def test_run_max_generation_attempts_exceeded(self):
        """Test _run method when max generation attempts exceeded"""
        self.tool._generation_count = 4
        
        result = self.tool._run(content=self.sample_content)
        self.assertIn("ERROR:", result)
        self.assertIn("Maximum generation attempts exceeded", result)

    @patch('src.tool.get_env_var')
    def test_run_no_api_key(self, mock_get_env_var):
        """Test _run method when API key is not found"""
        mock_get_env_var.return_value = None
        
        result = self.tool._run(content=self.sample_content)
        self.assertIn("ERROR:", result)
        self.assertIn("OpenAI API key not found", result)

    @patch('src.tool.openai.OpenAI')
    @patch('src.tool.get_env_var')
    @patch('src.tool.time.sleep')
    def test_run_successful_generation(self, mock_sleep, mock_get_env_var, mock_openai):
        """Test successful blog generation"""
        mock_get_env_var.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated blog content " * 100
        mock_client.chat.completions.create.return_value = mock_response
        
        result = self.tool._run(content=self.sample_content)
        self.assertNotIn("ERROR:", result)
        self.assertGreater(len(result), 100)

    @patch('src.tool.openai.OpenAI')
    @patch('src.tool.get_env_var')
    @patch('src.tool.time.sleep')
    def test_run_api_exception_with_retries(self, mock_sleep, mock_get_env_var, mock_openai):
        """Test _run method with API exceptions and retries"""
        mock_get_env_var.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        result = self.tool._run(content=self.sample_content)
        self.assertIn("ERROR:", result)
        self.assertIn("Could not generate blog article", result)

    @patch('src.tool.openai.OpenAI')
    @patch('src.tool.get_env_var')
    def test_run_content_too_short_after_generation(self, mock_get_env_var, mock_openai):
        """Test _run method when generated content is too short"""
        mock_get_env_var.return_value = "test-api-key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Short"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = self.tool._run(content=self.sample_content)
        self.assertIn("ERROR:", result)
        self.assertIn("Generated content too short", result)

    def test_run_with_kwargs_content_extraction(self):
        """Test _run method with content extraction from kwargs"""
        result = self.tool._run(context=self.sample_content)
        # Should not error due to content extraction
        self.assertTrue(len(result) > 0)


class TestPDFGeneratorTool(unittest.TestCase):
    """Comprehensive test suite for PDFGeneratorTool"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = PDFGeneratorTool()
        self.sample_content = "Test PDF Content\n\nThis is a paragraph.\n\nAnother paragraph."

    def test_init_creates_styles(self):
        """Test that initialization creates styles"""
        self.assertIsNotNone(self.tool.styles)
        self.assertIn('Title', self.tool.styles)
        self.assertIn('Normal', self.tool.styles)
        self.assertIn('Heading1', self.tool.styles)

    @patch('src.tool.getSampleStyleSheet')
    def test_create_styles_exception_fallback(self, mock_get_styles):
        """Test style creation when exception occurs"""
        # Mock the exception on the first call, success on fallback
        mock_get_styles.side_effect = [Exception("Style Error"), mock.MagicMock()]

        with patch('src.tool.logger') as mock_logger:
            try:
                tool = PDFGeneratorTool()
                # Should fallback to getSampleStyleSheet and succeed
                self.assertIsNotNone(tool.styles)
            except Exception:
                # If exception still occurs, verify the fallback logic
                self.fail("PDFGeneratorTool should handle style creation exceptions gracefully")

    def test_process_content_for_pdf_empty(self):
        """Test PDF content processing with empty content"""
        result = self.tool._process_content_for_pdf("")
        self.assertEqual(result, "No content available")

    def test_process_content_for_pdf_normal(self):
        """Test PDF content processing with normal content"""
        content = "Line 1\n\n\nLine 2\n\n\n\nLine 3"
        result = self.tool._process_content_for_pdf(content)
        self.assertNotIn("\n\n\n", result)
        self.assertIn("Line 1", result)
        self.assertIn("Line 2", result)

    def test_extract_title_with_content(self):
        """Test title extraction from content"""
        content = "Main Title\nSubtitle\nContent here"
        result = self.tool._extract_title(content)
        self.assertEqual(result, "Main Title")

    def test_extract_title_empty_content(self):
        """Test title extraction with empty content"""
        result = self.tool._extract_title("")
        self.assertEqual(result, "")

    def test_extract_title_whitespace_content(self):
        """Test title extraction with whitespace content"""
        content = "   \n\n  \n"
        result = self.tool._extract_title(content)
        self.assertEqual(result, "")

    @patch('src.tool.SimpleDocTemplate')
    @patch('src.tool.io.BytesIO')
    def test_generate_pdf_bytes_success(self, mock_bytesio, mock_doc):
        """Test successful PDF generation"""
        mock_buffer = MagicMock()
        mock_buffer.getvalue.return_value = b'PDF content'
        mock_bytesio.return_value = mock_buffer
        
        mock_doc_instance = MagicMock()
        mock_doc.return_value = mock_doc_instance
        
        result = self.tool.generate_pdf_bytes(self.sample_content)
        self.assertEqual(result, b'PDF content')
        mock_doc_instance.build.assert_called_once()

    def test_generate_pdf_bytes_fallback_on_exception(self):
        """Test PDF generation fallback when main method fails"""
        with patch('src.tool.SimpleDocTemplate', side_effect=Exception("PDF Error")):
            result = self.tool.generate_pdf_bytes(self.sample_content)
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)

    def test_add_content_to_pdf_normal_content(self):
        """Test adding content to PDF with normal formatting"""
        elements = []
        styles = self.tool.styles
        content = "Title\n\nParagraph 1\n\nParagraph 2"
        
        self.tool._add_content_to_pdf(content, elements, styles)
        self.assertGreater(len(elements), 0)

    def test_add_content_to_pdf_with_headings(self):
        """Test adding content to PDF with headings"""
        elements = []
        styles = self.tool.styles
        content = "# Main Heading\n\nContent here\n\nUPPERCASE HEADING\n\nMore content"
        
        self.tool._add_content_to_pdf(content, elements, styles)
        self.assertGreater(len(elements), 0)

    def test_add_content_to_pdf_empty_lines(self):
        """Test adding content to PDF with empty lines"""
        elements = []
        styles = self.tool.styles
        content = "Line 1\n\n\n\nLine 2\n\n"
        
        self.tool._add_content_to_pdf(content, elements, styles)
        self.assertGreater(len(elements), 0)

    @patch('src.tool.canvas.Canvas')
    @patch('src.tool.io.BytesIO')
    def test_generate_fallback_pdf_success(self, mock_bytesio, mock_canvas):
        """Test fallback PDF generation success"""
        mock_buffer = MagicMock()
        mock_buffer.getvalue.return_value = b'Fallback PDF content'
        mock_bytesio.return_value = mock_buffer
        
        mock_canvas_instance = MagicMock()
        mock_canvas.return_value = mock_canvas_instance
        mock_canvas_instance.stringWidth.return_value = 100
        
        result = self.tool._generate_fallback_pdf(self.sample_content)
        self.assertEqual(result, b'Fallback PDF content')

    @patch('src.tool.canvas.Canvas')
    @patch('src.tool.io.BytesIO')
    def test_generate_fallback_pdf_exception(self, mock_bytesio, mock_canvas):
        """Test fallback PDF generation when canvas fails"""
        # Setup BytesIO mock
        mock_buffer = MagicMock()
        mock_buffer.getvalue.return_value = b'Fallback content'
        mock_bytesio.return_value = mock_buffer
        
        # Make Canvas fail on first call, succeed on fallback
        mock_canvas.side_effect = [Exception("Canvas Error"), MagicMock()]
        
        with patch('src.tool.logger') as mock_logger:
            result = self.tool._generate_fallback_pdf("test content")
            self.assertIsInstance(result, bytes)
            self.assertGreater(len(result), 0)
            # Verify that an error was logged
            mock_logger.error.assert_called()


    @patch('src.tool.canvas.Canvas')
    @patch('src.tool.io.BytesIO')
    def test_generate_fallback_pdf_long_content(self, mock_bytesio, mock_canvas):
        """Test fallback PDF generation with long content"""
        mock_buffer = MagicMock()
        mock_buffer.getvalue.return_value = b'Long PDF content'
        mock_bytesio.return_value = mock_buffer
        
        mock_canvas_instance = MagicMock()
        mock_canvas.return_value = mock_canvas_instance
        mock_canvas_instance.stringWidth.side_effect = lambda text, font, size: len(text) * 5
        
        long_content = "This is a very long content " * 100
        result = self.tool._generate_fallback_pdf(long_content)
        self.assertEqual(result, b'Long PDF content')

    @patch('src.tool.canvas.Canvas')
    @patch('src.tool.io.BytesIO')
    def test_generate_fallback_pdf_page_break(self, mock_bytesio, mock_canvas):
        """Test fallback PDF generation with page breaks"""
        mock_buffer = MagicMock()
        mock_buffer.getvalue.return_value = b'Multi-page PDF'
        mock_bytesio.return_value = mock_buffer
        
        mock_canvas_instance = MagicMock()
        mock_canvas.return_value = mock_canvas_instance
        mock_canvas_instance.stringWidth.return_value = 50
        
        # Create content that will trigger page breaks
        content = " ".join(["word"] * 200)
        result = self.tool._generate_fallback_pdf(content)
        self.assertEqual(result, b'Multi-page PDF')


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    @patch('src.tool.os.getenv')
    def test_get_env_var_azure_name_found(self, mock_getenv):
        """Test get_env_var when Azure name is found"""
        mock_getenv.side_effect = lambda key: "azure_value" if key == "azure_key" else None
        
        result = get_env_var("azure_key", "traditional_key", "default")
        self.assertEqual(result, "azure_value")

    @patch('src.tool.os.getenv')
    def test_get_env_var_traditional_name_found(self, mock_getenv):
        """Test get_env_var when traditional name is found"""
        mock_getenv.side_effect = lambda key: "traditional_value" if key == "traditional_key" else None
        
        result = get_env_var("azure_key", "traditional_key", "default")
        self.assertEqual(result, "traditional_value")

    @patch('src.tool.os.getenv')
    def test_get_env_var_default_returned(self, mock_getenv):
        """Test get_env_var when default is returned"""
        mock_getenv.return_value = None
        
        result = get_env_var("azure_key", "traditional_key", "default")
        self.assertEqual(result, "default")

    @patch('src.tool.os.getenv')
    def test_get_env_var_no_default(self, mock_getenv):
        """Test get_env_var when no default is provided"""
        mock_getenv.return_value = None
        
        result = get_env_var("azure_key", "traditional_key")
        self.assertIsNone(result)


class TestModelClasses(unittest.TestCase):
    """Test Pydantic model classes"""
    
    def test_transcript_input_model_valid(self):
        """Test TranscriptInput model with valid data"""
        valid_input = TranscriptInput(
            youtube_url="https://www.youtube.com/watch?v=test",
            language="en"
        )
        self.assertEqual(valid_input.youtube_url, "https://www.youtube.com/watch?v=test")
        self.assertEqual(valid_input.language, "en")

    def test_transcript_input_model_default_language(self):
        """Test TranscriptInput model with default language"""
        default_input = TranscriptInput(youtube_url="https://www.youtube.com/watch?v=test")
        self.assertEqual(default_input.language, "en")

    def test_transcript_input_model_custom_language(self):
        """Test TranscriptInput model with custom language"""
        custom_input = TranscriptInput(
            youtube_url="https://www.youtube.com/watch?v=test",
            language="es"
        )
        self.assertEqual(custom_input.language, "es")

    def test_blog_input_model_valid(self):
        """Test BlogInput model with valid data"""
        valid_input = BlogInput(content="Test content")
        self.assertEqual(valid_input.content, "Test content")

    def test_blog_input_model_empty_content(self):
        """Test BlogInput model with empty content"""
        empty_input = BlogInput(content="")
        self.assertEqual(empty_input.content, "")


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for complex scenarios"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.youtube_tool = YouTubeTranscriptTool()
        self.blog_tool = BlogGeneratorTool()
        self.pdf_tool = PDFGeneratorTool()

    @patch('src.tool.time.sleep')
    def test_tool_state_management_across_calls(self, mock_sleep):
        """Test tool state management across multiple calls"""
        # Test YouTube tool state
        initial_count = self.youtube_tool._call_count
        self.youtube_tool._call_count += 1
        self.assertGreater(self.youtube_tool._call_count, initial_count)
        
        # Test Blog tool state
        self.blog_tool._generation_count += 1
        self.assertEqual(self.blog_tool._generation_count, 1)

    def test_content_flow_between_tools(self):
        """Test content flow from transcript to blog to PDF"""
        # Simulate transcript content
        transcript_content = "Docker wins the container category. Kubernetes vs Docker comparison."
        
        # Test key information extraction
        key_info = self.blog_tool._extract_key_information(transcript_content)
        self.assertIn('Docker', key_info['tools'])
        
        # Test PDF content processing
        pdf_content = self.pdf_tool._process_content_for_pdf(transcript_content)
        self.assertIn('Docker', pdf_content)

    def test_error_handling_chain(self):
        """Test error handling across tool chain"""
        # Test YouTube tool error handling
        result = self.youtube_tool._run("invalid_url")
        self.assertIn("ERROR:", result)
        
        # Test Blog tool error handling
        result = self.blog_tool._run(content="")
        self.assertIn("ERROR:", result)

    def test_content_preservation_chain(self):
        """Test that technical content is preserved through the chain"""
        technical_content = "Fabric API wins. DevBox vs Docker comparison. Version 1.2.3 released."
        
        # Test transcript cleaning preserves technical terms
        cleaned = self.youtube_tool._enhanced_clean_transcript(technical_content)
        self.assertIn("Fabric", cleaned)
        self.assertIn("DevBox", cleaned)
        
        # Test blog tool preserves technical information
        key_info = self.blog_tool._extract_key_information(technical_content)
        self.assertIn("Fabric", key_info['tools'])
        self.assertIn("1.2.3", key_info['versions'])


if __name__ == '__main__':
    # Configure test runner for coverage
    unittest.main(verbosity=2, buffer=True)
