from unittest.mock import MagicMock, Mock, patch

import pytest


class TestBlogGeneratorTool:
    """Test cases for BlogGeneratorTool"""

    def test_init_success(self):
        """Test successful initialization"""
        from app.services.blog_service import BlogGeneratorTool

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            assert tool is not None

    def test_init_missing_api_key(self):
        """Test initialization with missing API key"""
        from app.services.blog_service import BlogGeneratorTool

        with patch('app.services.blog_service.OPENAI_API_KEY', None):
            with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
                BlogGeneratorTool()

    def test_run_success(self):
        """Test successful blog generation"""
        from app.services.blog_service import BlogGeneratorTool

        transcript = "This is a test transcript about AI technology and machine learning applications in modern software development."
        expected_blog = "# Test Blog Post\n\nThis is a comprehensive blog post about technology."

        # Mock the OpenAI client context
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), \
                patch('app.services.blog_service.openai_client_context') as mock_context:

            # Setup mock OpenAI client
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = expected_blog
            mock_client.chat.completions.create.return_value = mock_response

            # Configure context manager
            mock_context.return_value.__enter__.return_value = mock_client
            mock_context.return_value.__exit__.return_value = None

            tool = BlogGeneratorTool()
            result = tool._run(transcript)

            assert not result.startswith('ERROR:')
            assert 'Test Blog Post' in result

    def test_run_empty_transcript(self):
        """Test blog generation with empty transcript"""
        from app.services.blog_service import BlogGeneratorTool

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            result = tool._run("")

            assert result.startswith('ERROR: Invalid or empty transcript')

    def test_run_short_transcript(self):
        """Test blog generation with too short transcript"""
        from app.services.blog_service import BlogGeneratorTool

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            result = tool._run("short")

            assert result.startswith('ERROR: Invalid or empty transcript')

    def test_run_error_transcript(self):
        """Test blog generation with error transcript"""
        from app.services.blog_service import BlogGeneratorTool

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            # Make the error input longer than 100 characters to bypass the
            # length check
            error_input = "ERROR: Previous step failed during transcript processing. This error occurred while attempting to extract and process the YouTube video content for blog generation."
            result = tool._run(error_input)

            # The function should return the error as-is since it starts with
            # "ERROR:"
            assert result == error_input

    def test_run_openai_exception(self):
        """Test blog generation with OpenAI API exception"""
        from app.services.blog_service import BlogGeneratorTool

        transcript = "This is a test transcript about AI technology and machine learning applications in modern software development."

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), \
                patch('app.services.blog_service.openai_client_context') as mock_context:

            mock_context.side_effect = Exception("OpenAI API error")

            tool = BlogGeneratorTool()
            result = tool._run(transcript)

            assert result.startswith('ERROR: Blog generation failed')

    def test_clean_markdown_content(self):
        """Test markdown content cleaning"""
        from app.services.blog_service import BlogGeneratorTool

        content = """**Bold text** and *italic text* with `code` and excess

        ___underscores___ and --- horizontal rules ---

        ||pipe symbols|| and multiple\n\n\n\nnewlines"""

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            result = tool._clean_markdown_content(content)

            assert '**' not in result
            assert '*' not in result
            assert '`' not in result
            assert '___' not in result
            assert '---' not in result
            assert '||' not in result
            assert '\n\n\n\n' not in result

    def test_clean_markdown_content_empty(self):
        """Test markdown content cleaning with empty content"""
        from app.services.blog_service import BlogGeneratorTool

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            result = tool._clean_markdown_content("")

            assert result == ""

    def test_clean_markdown_content_headings(self):
        """Test markdown content cleaning with headings"""
        from app.services.blog_service import BlogGeneratorTool

        content = """#### Too many hashes
        ### Three hashes
        ## Two hashes
        # One hash"""

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            tool = BlogGeneratorTool()
            result = tool._clean_markdown_content(content)

            assert '####' not in result
            assert '### Too many hashes' in result


class TestBlogServiceFunctions:
    """Test cases for blog service functions"""

    def test_extract_video_id_youtube_watch(self):
        """Test video ID extraction from youtube.com/watch URL"""
        from app.services.blog_service import _extract_video_id

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = _extract_video_id(url)

        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_youtu_be(self):
        """Test video ID extraction from youtu.be URL"""
        from app.services.blog_service import _extract_video_id

        url = "https://youtu.be/dQw4w9WgXcQ"
        result = _extract_video_id(url)

        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_embed(self):
        """Test video ID extraction from embed URL"""
        from app.services.blog_service import _extract_video_id

        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = _extract_video_id(url)

        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_shorts(self):
        """Test video ID extraction from shorts URL"""
        from app.services.blog_service import _extract_video_id

        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        result = _extract_video_id(url)

        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_mobile(self):
        """Test video ID extraction from mobile URL"""
        from app.services.blog_service import _extract_video_id

        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        result = _extract_video_id(url)

        assert result == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test video ID extraction from invalid URL"""
        from app.services.blog_service import _extract_video_id

        url = "https://www.example.com/video"
        result = _extract_video_id(url)

        assert result is None

    def test_extract_video_id_empty_url(self):
        """Test video ID extraction from empty URL"""
        from app.services.blog_service import _extract_video_id

        result = _extract_video_id("")

        assert result is None

    def test_extract_video_id_none_url(self):
        """Test video ID extraction from None URL"""
        from app.services.blog_service import _extract_video_id

        result = _extract_video_id(None)

        assert result is None

    def test_clean_final_output(self):
        """Test final output cleaning"""
        from app.services.blog_service import _clean_final_output

        content = """Action: BlogGeneratorTool
        Tool: YouTubeTranscriptTool
        {"some": "json"} and {unmatched braces}
        ***excess asterisks*** and ---horizontal rules---

        # Heading 1
        ## Heading 2

        Regular paragraph text."""

        result = _clean_final_output(content)

        assert 'Action:' not in result
        assert 'Tool:' not in result
        assert 'BlogGeneratorTool' not in result
        assert '{"some": "json"}' not in result
        assert '***' not in result
        assert '---' not in result
        assert '# Heading 1' in result
        assert '## Heading 2' in result

    def test_clean_final_output_empty(self):
        """Test final output cleaning with empty content"""
        from app.services.blog_service import _clean_final_output

        result = _clean_final_output("")

        assert result == ""

    def test_create_error_response(self):
        """Test error response creation"""
        from app.services.blog_service import _create_error_response

        url = "https://www.youtube.com/watch?v=test123"
        error_msg = "Test error message"

        result = _create_error_response(url, error_msg)

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert url in result
        assert error_msg in result
        assert 'Troubleshooting Steps' in result
        assert 'Alternative Approaches' in result

    def test_generate_blog_from_youtube_missing_openai_key(self):
        """Test blog generation with missing OpenAI API key"""
        from app.services.blog_service import generate_blog_from_youtube

        with patch.dict('os.environ', {}, clear=True), \
                patch('os.getenv') as mock_getenv:

            # Mock environment variables to return None for OPENAI_API_KEY
            def getenv_side_effect(key, default=None):
                if key == 'OPENAI_API_KEY':
                    return None
                elif key == 'SUPADATA_API_KEY':
                    return 'test-key'
                return default

            mock_getenv.side_effect = getenv_side_effect

            result = generate_blog_from_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            assert 'OpenAI API key not found' in result
            assert result.startswith(
                '# YouTube Video Analysis - Technical Issue')

    def test_generate_blog_from_youtube_missing_supadata_key(self):
        """Test blog generation with missing Supadata API key"""
        from app.services.blog_service import generate_blog_from_youtube

        with patch.dict('os.environ', {}, clear=True), \
                patch('os.getenv') as mock_getenv:

            # Mock environment variables to return None for SUPADATA_API_KEY
            def getenv_side_effect(key, default=None):
                if key == 'OPENAI_API_KEY':
                    return 'test-key'
                elif key == 'SUPADATA_API_KEY':
                    return None
                return default

            mock_getenv.side_effect = getenv_side_effect

            result = generate_blog_from_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            assert 'SUPADATA_API_KEY not found' in result
            assert result.startswith(
                '# YouTube Video Analysis - Technical Issue')

    def test_generate_blog_from_youtube_invalid_url(self):
        """Test blog generation with invalid YouTube URL"""
        from app.services.blog_service import generate_blog_from_youtube

        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test-key'  # Mock both API keys as available

            result = generate_blog_from_youtube(
                "https://www.example.com/video")

            assert 'Invalid YouTube URL' in result
            assert result.startswith(
                '# YouTube Video Analysis - Technical Issue')

    def test_generate_blog_from_youtube_empty_url(self):
        """Test blog generation with empty URL"""
        from app.services.blog_service import generate_blog_from_youtube

        with patch('os.getenv') as mock_getenv:
            mock_getenv.return_value = 'test-key'

            result = generate_blog_from_youtube("")

            assert 'Invalid YouTube URL' in result

    def test_generate_blog_from_youtube_success(self):
        """Test successful blog generation"""
        from app.services.blog_service import generate_blog_from_youtube

        expected_content = "# Test Blog Post\n\nThis is a comprehensive test blog post about technology trends and innovations in the modern era. " \
            "It covers various aspects of technological advancement, including artificial intelligence, machine learning, " \
            "cloud computing, cybersecurity, and digital transformation. The blog post discusses how these technologies " \
            "are reshaping industries and creating new opportunities for businesses and individuals alike. " \
            "We explore the latest developments in each field and provide insights into future trends and predictions."

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'}), \
                patch('app.services.blog_service.individual_components_test') as mock_test:

            mock_test.return_value = expected_content

            result = generate_blog_from_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            # Check that the result is the expected content (successful case)
            assert result == expected_content
            assert 'Test Blog Post' in result

    def test_generate_blog_from_youtube_short_result(self):
        """Test blog generation with short result"""
        from app.services.blog_service import generate_blog_from_youtube

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'}), \
                patch('app.services.blog_service.individual_components_test') as mock_test:

            mock_test.return_value = "Short result"  # Less than 500 characters

            result = generate_blog_from_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            # This will generate an error response with the header
            assert '# YouTube Video Analysis - Technical Issue' in result
            assert 'Could not generate blog content' in result

    def test_generate_blog_from_youtube_exception(self):
        """Test blog generation with exception"""
        from app.services.blog_service import generate_blog_from_youtube

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'}), \
                patch('app.services.blog_service.individual_components_test') as mock_test:

            mock_test.side_effect = Exception("Unexpected error occurred")

            result = generate_blog_from_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            # The function creates an error response that contains the
            # exception message
            assert '# YouTube Video Analysis - Technical Issue' in result
            assert 'Unexpected error: Unexpected error occurred' in result

    def test_individual_components_test_success(self):
        """Test successful individual components test"""
        from app.services.blog_service import individual_components_test

        mock_transcript = "This is a comprehensive test transcript about artificial intelligence and machine learning technologies."
        mock_blog_content = "# AI Technology Blog\n\nThis blog discusses the latest trends in artificial intelligence and machine learning."

        with patch('app.services.youtube_service.YouTubeTranscriptTool') as mock_yt_tool, \
                patch('app.services.blog_service.BlogGeneratorTool') as mock_blog_tool:

            # Mock transcript tool
            mock_yt_instance = Mock()
            mock_yt_instance._run.return_value = mock_transcript
            mock_yt_tool.return_value = mock_yt_instance

            # Mock blog generator tool
            mock_blog_instance = Mock()
            mock_blog_instance._run.return_value = mock_blog_content
            mock_blog_tool.return_value = mock_blog_instance

            result = individual_components_test(
                "https://www.youtube.com/watch?v=test123")

            assert result == mock_blog_content
            mock_yt_instance._run.assert_called_once_with(
                "https://www.youtube.com/watch?v=test123", "en")
            mock_blog_instance._run.assert_called_once_with(mock_transcript)

    def test_individual_components_test_transcript_error(self):
        """Test individual components test with transcript error"""
        from app.services.blog_service import individual_components_test

        with patch('app.services.youtube_service.YouTubeTranscriptTool') as mock_yt_tool:
            mock_yt_instance = Mock()
            mock_yt_instance._run.return_value = "ERROR: Transcript extraction failed"
            mock_yt_tool.return_value = mock_yt_instance

            result = individual_components_test(
                "https://www.youtube.com/watch?v=test123")

            assert 'Transcript extraction failed' in result
            assert result.startswith(
                '# YouTube Video Analysis - Technical Issue')

    def test_individual_components_test_blog_error(self):
        """Test individual components test with blog generation error"""
        from app.services.blog_service import individual_components_test

        mock_transcript = "This is a test transcript about technology."

        with patch('app.services.youtube_service.YouTubeTranscriptTool') as mock_yt_tool, \
                patch('app.services.blog_service.BlogGeneratorTool') as mock_blog_tool:

            # Mock transcript tool success
            mock_yt_instance = Mock()
            mock_yt_instance._run.return_value = mock_transcript
            mock_yt_tool.return_value = mock_yt_instance

            # Mock blog generator tool error
            mock_blog_instance = Mock()
            mock_blog_instance._run.return_value = "ERROR: Blog generation failed"
            mock_blog_tool.return_value = mock_blog_instance

            result = individual_components_test(
                "https://www.youtube.com/watch?v=test123")

            assert 'Blog generation failed' in result
            assert result.startswith(
                '# YouTube Video Analysis - Technical Issue')

    def test_individual_components_test_exception(self):
        """Test individual components test with exception"""
        from app.services.blog_service import individual_components_test

        with patch('app.services.youtube_service.YouTubeTranscriptTool') as mock_yt_tool:
            mock_yt_tool.side_effect = Exception("Tool initialization failed")

            result = individual_components_test(
                "https://www.youtube.com/watch?v=test123")

            assert 'Component test failed: Tool initialization failed' in result
            assert result.startswith(
                '# YouTube Video Analysis - Technical Issue')

    def test_individual_components_test_with_language(self):
        """Test individual components test with specific language"""
        from app.services.blog_service import individual_components_test

        mock_transcript = "Este es un transcript de prueba sobre tecnología."
        mock_blog_content = "# Blog de Tecnología\n\nEste blog discute las últimas tendencias en tecnología."

        with patch('app.services.youtube_service.YouTubeTranscriptTool') as mock_yt_tool, \
                patch('app.services.blog_service.BlogGeneratorTool') as mock_blog_tool:

            # Mock transcript tool
            mock_yt_instance = Mock()
            mock_yt_instance._run.return_value = mock_transcript
            mock_yt_tool.return_value = mock_yt_instance

            # Mock blog generator tool
            mock_blog_instance = Mock()
            mock_blog_instance._run.return_value = mock_blog_content
            mock_blog_tool.return_value = mock_blog_instance

            result = individual_components_test(
                "https://www.youtube.com/watch?v=test123", "es")

            assert result == mock_blog_content
            mock_yt_instance._run.assert_called_once_with(
                "https://www.youtube.com/watch?v=test123", "es")


class TestOpenAIClientContext:
    """Test cases for OpenAI client context manager"""

    def test_openai_client_context_success(self):
        """Test successful OpenAI client context"""
        from app.services.blog_service import openai_client_context

        with patch('builtins.__import__') as mock_import, \
                patch('app.services.blog_service.OPENAI_API_KEY', 'test-key'):

            # Mock the OpenAI import and client
            mock_openai_module = Mock()
            mock_openai_class = Mock()
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_openai_module.OpenAI = mock_openai_class

            def import_side_effect(name, *args, **kwargs):
                if name == 'openai':
                    return mock_openai_module
                # For other imports, use the real import
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            with openai_client_context() as client:
                assert client == mock_client
                mock_openai_class.assert_called_once_with(api_key='test-key')

    def test_openai_client_context_exception(self):
        """Test OpenAI client context with exception"""
        from app.services.blog_service import openai_client_context

        with patch('builtins.__import__') as mock_import:
            def import_side_effect(name, *args, **kwargs):
                if name == 'openai':
                    raise ImportError("OpenAI not installed")
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            with pytest.raises(Exception):
                with openai_client_context() as client:
                    pass

    def test_openai_client_context_cleanup(self):
        """Test OpenAI client context cleanup"""
        from app.services.blog_service import openai_client_context

        with patch('builtins.__import__') as mock_import, \
                patch('app.services.blog_service.gc.collect') as mock_gc, \
                patch('app.services.blog_service.OPENAI_API_KEY', 'test-key'):

            # Mock the OpenAI import and client
            mock_openai_module = Mock()
            mock_openai_class = Mock()
            mock_client = Mock()
            mock_openai_class.return_value = mock_client
            mock_openai_module.OpenAI = mock_openai_class

            def import_side_effect(name, *args, **kwargs):
                if name == 'openai':
                    return mock_openai_module
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            with openai_client_context() as client:
                pass

            # Verify cleanup was called
            mock_gc.assert_called_once()
