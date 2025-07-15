import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import logging
from io import StringIO
from src.main import (
    _extract_video_id,
    _clean_final_output,
    _create_error_response,
    individual_components_test,
    generate_blog_from_youtube,
    validate_environment,
    cli_main
)

# Mock classes for tools
class MockYouTubeTranscriptTool:
    def _run(self, url, language):
        if "error" in url:
            return "ERROR: Test error"
        return "Sample transcript" * 10

class MockBlogGeneratorTool:
    def _run(self, transcript):
        if "error" in transcript:
            return "ERROR: Test error"
        return "Generated blog" * 100

class TestMainFunctions(unittest.TestCase):
    
    def setUp(self):
        # Redirect logger output
        self.log_capture = StringIO()
        logging.basicConfig(stream=self.log_capture, level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    # Test _extract_video_id
    def test_extract_video_id_valid_urls(self):
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/embed/dQw4w9WgXcQ",
            "https://youtube.com/v/dQw4w9WgXcQ",
            "https://youtube.com/shorts/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/live/dQw4w9WgXcQ"
        ]
        for url in urls:
            self.assertEqual(_extract_video_id(url), "dQw4w9WgXcQ")
    
    def test_extract_video_id_invalid_urls(self):
        urls = [
            "https://invalid.com/watch?v=123",
            "https://youtube.com/playlist?list=123",
            "",
            None
        ]
        for url in urls:
            self.assertIsNone(_extract_video_id(url))
    
    def test_extract_video_id_edge_cases(self):
        # Test with additional parameters
        url_with_params = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s"
        self.assertEqual(_extract_video_id(url_with_params), "dQw4w9WgXcQ")
        
        # Test with invalid video ID length
        invalid_id_url = "https://www.youtube.com/watch?v=abc123"
        self.assertIsNone(_extract_video_id(invalid_id_url))
    
    # Test _clean_final_output - FIXED
    def test_clean_final_output(self):
        dirty_content = """
        Action: Generate
        Tool: YouTubeTool
        {
          "content": "Some JSON"
        }
        ###Heading
        * Item 1
        * Item 2
        ---
        """
        cleaned = _clean_final_output(dirty_content)
        
        # Should remove tool mentions
        self.assertNotIn("Action:", cleaned)
        self.assertNotIn("Tool:", cleaned)
        
        # Should remove JSON artifacts
        self.assertNotIn("{", cleaned)
        self.assertNotIn("}", cleaned)
        
        # The function transforms ###Heading to ### Heading (adds space)
        self.assertIn("### Heading", cleaned)
        
        # Should fix list formatting
        self.assertIn("- Item 1", cleaned)
        self.assertIn("- Item 2", cleaned)
        
        # Should remove horizontal rules
        self.assertNotIn("---", cleaned)
    
    def test_clean_final_output_empty(self):
        self.assertEqual(_clean_final_output(""), "")
        self.assertEqual(_clean_final_output(None), "")

    def test_clean_final_output_complex(self):
        complex_content = """
        # Main Title
        
        ## Section 1
        
        ### Subsection
        
        - List item 1
        - List item 2
        
        1. Numbered item 1
        2. Numbered item 2
        
        Regular paragraph text.
        """
        cleaned = _clean_final_output(complex_content)
        self.assertIn("# Main Title", cleaned)
        self.assertIn("## Section 1", cleaned)
        self.assertIn("### Subsection", cleaned)

    # Test _create_error_response
    def test_create_error_response(self):
        response = _create_error_response("https://youtu.be/abc", "Test error")
        self.assertIn("YouTube Video Analysis", response)
        self.assertIn("https://youtu.be/abc", response)
        self.assertIn("Test error", response)
        self.assertIn("Troubleshooting Steps", response)

    def test_create_error_response_formatting(self):
        response = _create_error_response("https://youtu.be/test123", "Network timeout")
        self.assertIn("**URL**: https://youtu.be/test123", response)
        self.assertIn("Network timeout", response)
        self.assertIn("Alternative Approaches", response)

    # Test individual_components_test - FIXED with correct import paths
    @patch('src.tool.YouTubeTranscriptTool')
    @patch('src.tool.BlogGeneratorTool')
    def test_individual_components_test_success(self, mock_blog_class, mock_transcript_class):
        # Create mock instances
        mock_transcript_instance = MockYouTubeTranscriptTool()
        mock_blog_instance = MockBlogGeneratorTool()
        
        # Set up the class mocks to return these instances
        mock_transcript_class.return_value = mock_transcript_instance
        mock_blog_class.return_value = mock_blog_instance
        
        result = individual_components_test("https://youtu.be/abc", "en")
        
        # Verify the result
        self.assertEqual(result, "Generated blog" * 100)
        
        # Verify classes were instantiated
        mock_transcript_class.assert_called_once()
        mock_blog_class.assert_called_once()

    @patch('src.tool.YouTubeTranscriptTool')
    def test_individual_components_test_transcript_fail(self, mock_transcript_class):
        mock_transcript_instance = MockYouTubeTranscriptTool()
        mock_transcript_class.return_value = mock_transcript_instance
        
        result = individual_components_test("https://error.com", "en")
        
        self.assertIn("Technical Issue Encountered", result)
        self.assertIn("ERROR: Test error", result)
        self.assertIn("YouTube Video Analysis", result)

    @patch('src.tool.YouTubeTranscriptTool')
    @patch('src.tool.BlogGeneratorTool')
    def test_individual_components_test_blog_fail(self, mock_blog_class, mock_transcript_class):
        # Setup transcript tool to work normally
        mock_transcript_instance = MockYouTubeTranscriptTool()
        mock_transcript_class.return_value = mock_transcript_instance
        
        # Setup blog tool to fail
        mock_blog_instance = Mock()
        mock_blog_instance._run.return_value = "ERROR: Blog generation failed"
        mock_blog_class.return_value = mock_blog_instance
        
        result = individual_components_test("https://youtu.be/abc", "en")
        
        self.assertIn("Technical Issue Encountered", result)
        self.assertIn("ERROR: Blog generation failed", result)

    @patch('src.tool.YouTubeTranscriptTool')
    def test_individual_components_test_exception(self, mock_transcript_class):
        # Make the transcript tool constructor raise an exception
        mock_transcript_class.side_effect = Exception("Tool initialization failed")
        
        result = individual_components_test("https://youtu.be/abc", "en")
        
        self.assertIn("Technical Issue Encountered", result)
        self.assertIn("Component test failed: Tool initialization failed", result)

    # Test validate_environment
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test", "SUPADATA_API_KEY": "test"}, clear=True)
    def test_validate_environment_success(self):
        try:
            validate_environment()
        except Exception as e:
            self.fail(f"validate_environment failed unexpectedly: {e}")

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_failure(self):
        with self.assertRaises(RuntimeError):
            validate_environment()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True)
    def test_validate_environment_partial_failure(self):
        with self.assertRaises(RuntimeError):
            validate_environment()

    # Test generate_blog_from_youtube
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test", "SUPADATA_API_KEY": "test"}, clear=True)
    @patch('src.main.individual_components_test')
    @patch('src.main._extract_video_id')
    def test_generate_blog_success(self, mock_extract, mock_test):
        mock_extract.return_value = "valid_id"
        mock_test.return_value = "Generated blog content" * 100  # >500 chars
        
        result = generate_blog_from_youtube("https://youtu.be/abc")
        
        self.assertNotIn("Technical Issue Encountered", result)
        self.assertGreater(len(result), 100)

    @patch.dict(os.environ, {}, clear=True)
    def test_generate_blog_missing_keys(self):
        result = generate_blog_from_youtube("https://youtu.be/abc")
        self.assertIn("OpenAI API key", result)

    def test_generate_blog_invalid_url(self):
        result = generate_blog_from_youtube("invalid_url")
        self.assertIn("Invalid YouTube URL", result)

    @patch('src.main._extract_video_id')
    def test_generate_blog_no_video_id(self, mock_extract):
        mock_extract.return_value = None
        result = generate_blog_from_youtube("https://youtu.be/abc")
        self.assertIn("Could not extract", result)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test", "SUPADATA_API_KEY": "test"}, clear=True)
    @patch('src.main.individual_components_test')
    @patch('src.main._extract_video_id')
    def test_generate_blog_short_output(self, mock_extract, mock_test):
        mock_extract.return_value = "valid_id"
        mock_test.return_value = "Short content"
        
        result = generate_blog_from_youtube("https://youtu.be/abc")
        self.assertIn("Could not generate", result)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test", "SUPADATA_API_KEY": "test"}, clear=True)
    @patch('src.main.individual_components_test')
    @patch('src.main._extract_video_id')
    def test_generate_blog_exception(self, mock_extract, mock_test):
        mock_extract.return_value = "valid_id"
        mock_test.side_effect = Exception("Unexpected error occurred")
        
        result = generate_blog_from_youtube("https://youtu.be/abc")
        self.assertIn("Unexpected error", result)

    # Test CLI main
    @patch('builtins.input', side_effect=["https://youtu.be/abc", "en"])
    @patch('src.main.generate_blog_from_youtube')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_cli_main_success(self, mock_open, mock_generate, mock_input):
        mock_generate.return_value = "Generated blog content"
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cli_main()
            output = fake_out.getvalue()
        
        self.assertIn("GENERATED BLOG ARTICLE", output)
        mock_open.assert_called_once()

    @patch('builtins.input', return_value="")
    def test_cli_main_no_url(self, mock_input):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cli_main()
            output = fake_out.getvalue()
        self.assertIn("YouTube URL is required", output)

    @patch('builtins.input', side_effect=["https://youtu.be/abc"])
    @patch('src.main.generate_blog_from_youtube', side_effect=Exception("Test error"))
    def test_cli_main_exception(self, mock_generate, mock_input):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cli_main()
            output = fake_out.getvalue()
        self.assertIn("Error:", output)

    @patch('builtins.input', side_effect=["https://youtu.be/abc", "en"])
    @patch('src.main.validate_environment', side_effect=RuntimeError("Missing environment variables"))
    def test_cli_main_env_error(self, mock_validate, mock_input):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cli_main()
            output = fake_out.getvalue()
        self.assertIn("Missing environment variables", output)

    @patch('builtins.input', side_effect=KeyboardInterrupt())
    def test_cli_main_keyboard_interrupt(self, mock_input):
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cli_main()
            output = fake_out.getvalue()
        self.assertIn("Operation cancelled", output)

    @patch('builtins.input', side_effect=["https://youtu.be/abc", ""])
    @patch('src.main.generate_blog_from_youtube')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_cli_main_default_language(self, mock_open, mock_generate, mock_input):
        mock_generate.return_value = "Generated blog content"
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cli_main()
            output = fake_out.getvalue()
        
        # Verify default language "en" was used
        mock_generate.assert_called_once_with("https://youtu.be/abc", "en")

if __name__ == '__main__':
    unittest.main()
