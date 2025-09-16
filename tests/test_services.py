from unittest.mock import MagicMock, mock_open, patch

import pytest

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

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_init_success(self):
        """Test successful initialization with API key"""
        from app.services.blog_service import BlogGeneratorTool

        tool = BlogGeneratorTool()
        assert tool is not None

    @patch('app.services.blog_service.OPENAI_API_KEY', None)
    def test_init_no_api_key(self):
        """Test initialization fails without API key"""
        from app.services.blog_service import BlogGeneratorTool

        with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
            BlogGeneratorTool()

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_run_invalid_transcript(self):
        """Test blog generation with invalid transcript"""
        from app.services.blog_service import BlogGeneratorTool

        tool = BlogGeneratorTool()
        result = tool._run('Short')

        assert result.startswith('ERROR:')
        assert 'Invalid or empty transcript' in result

    @patch('app.services.blog_service.OPENAI_API_KEY', 'test-key')
    def test_run_error_transcript(self):
        """Test blog generation with error transcript"""
        from app.services.blog_service import BlogGeneratorTool

        tool = BlogGeneratorTool()
        # Make sure error transcript is long enough to pass length validation
        error_transcript = 'ERROR: Something went wrong with the transcript extraction process and this message is long enough to pass validation'
        result = tool._run(error_transcript)

        assert result == error_transcript

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('app.services.blog_service.openai_client_context')
    def test_run_success(self, mock_context):
        """Test successful blog generation"""
        from app.services.blog_service import BlogGeneratorTool

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "# Test Blog\n\nThis is a test blog post."
        mock_client.chat.completions.create.return_value = mock_response
        mock_context.return_value.__enter__.return_value = mock_client

        tool = BlogGeneratorTool()
        result = tool._run("This is a long transcript with enough content to pass validation. " * 10)

        assert "Test Blog" in result
        assert not result.startswith('ERROR:')

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('app.services.blog_service.openai_client_context')
    def test_run_openai_error(self, mock_context):
        """Test blog generation with OpenAI API error"""
        from app.services.blog_service import BlogGeneratorTool

        mock_context.side_effect = Exception("API Error")

        tool = BlogGeneratorTool()
        result = tool._run("This is a long transcript with enough content to pass validation. " * 10)

        assert result.startswith('ERROR:')
        assert 'Blog generation failed' in result

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_clean_markdown_content_basic(self):
        """Test basic markdown content cleaning"""
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

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_clean_markdown_content_empty(self):
        """Test cleaning empty content"""
        from app.services.blog_service import BlogGeneratorTool

        tool = BlogGeneratorTool()
        result = tool._clean_markdown_content("")

        assert result == ""

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_clean_markdown_content_complex(self):
        """Test cleaning complex markdown artifacts"""
        from app.services.blog_service import BlogGeneratorTool

        tool = BlogGeneratorTool()

        input_content = """
        #### Too many hashes



        Too many newlines

        ______
        ---
        ||pipes||
        `inline code`

        * asterisk list
        1.numbered list
        """

        result = tool._clean_markdown_content(input_content)

        # Should reduce to max 3 hash levels
        assert '### Too many hashes' in result
        # Should not have excessive newlines
        assert '\n\n\n' not in result
        # Should convert asterisk lists to dashes
        assert '- asterisk list' in result
        # Should fix numbered lists
        assert '1. numbered list' in result or '1.numbered list' in result


class TestBlogServiceFunctions:

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'})
    @patch('app.services.blog_service.individual_components_test')
    @patch('app.services.blog_service._extract_video_id')
    def test_generate_blog_from_youtube_success(self, mock_extract_id, mock_individual_test):
        """Test successful blog generation from YouTube URL"""
        from app.services.blog_service import generate_blog_from_youtube

        mock_extract_id.return_value = "dQw4w9WgXcQ"  # Valid video ID
        mock_individual_test.return_value = "This is a long generated blog content with enough text to pass validation."

        result = generate_blog_from_youtube('https://youtube.com/watch?v=dQw4w9WgXcQ')

        assert len(result) > 500
        assert not result.startswith('ERROR:')
        mock_individual_test.assert_called_once()

    @patch.dict('os.environ', {}, clear=True)
    def test_generate_blog_missing_openai_key(self):
        """Test blog generation with missing OpenAI API key"""
        from app.services.blog_service import generate_blog_from_youtube

        result = generate_blog_from_youtube('https://youtube.com/watch?v=test123')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'OpenAI API key not found' in result

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=True)
    def test_generate_blog_missing_supadata_key(self):
        """Test blog generation with missing Supadata API key"""
        from app.services.blog_service import generate_blog_from_youtube

        result = generate_blog_from_youtube('https://youtube.com/watch?v=test123')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'SUPADATA_API_KEY not found' in result

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'})
    def test_generate_blog_invalid_url(self):
        """Test blog generation with invalid YouTube URL"""
        from app.services.blog_service import generate_blog_from_youtube

        result = generate_blog_from_youtube('https://invalid-url.com')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'Invalid YouTube URL provided' in result

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'})
    def test_generate_blog_no_video_id(self):
        """Test blog generation when video ID cannot be extracted"""
        from app.services.blog_service import generate_blog_from_youtube

        result = generate_blog_from_youtube('https://youtube.com/watch?v=')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'Could not extract valid video ID' in result

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'})
    @patch('app.services.blog_service.individual_components_test')
    @patch('app.services.blog_service._extract_video_id')
    def test_generate_blog_short_result(self, mock_extract_id, mock_individual_test):
        """Test blog generation with short result content"""
        from app.services.blog_service import generate_blog_from_youtube

        mock_extract_id.return_value = "dQw4w9WgXcQ"
        mock_individual_test.return_value = "Short content"

        result = generate_blog_from_youtube('https://youtube.com/watch?v=dQw4w9WgXcQ')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'Could not generate blog content' in result

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key', 'SUPADATA_API_KEY': 'test-key'})
    @patch('app.services.blog_service.individual_components_test')
    @patch('app.services.blog_service._extract_video_id')
    def test_generate_blog_exception(self, mock_extract_id, mock_individual_test):
        """Test blog generation with exception during processing"""
        from app.services.blog_service import generate_blog_from_youtube

        mock_extract_id.return_value = "dQw4w9WgXcQ"
        mock_individual_test.side_effect = Exception("Test exception")

        result = generate_blog_from_youtube('https://youtube.com/watch?v=dQw4w9WgXcQ')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'Unexpected error: Test exception' in result

    @patch('app.services.youtube_service.YouTubeTranscriptTool')
    @patch('app.services.blog_service.BlogGeneratorTool')
    def test_individual_components_test_success(self, mock_blog_tool, mock_transcript_tool):
        """Test successful individual components test"""
        from app.services.blog_service import individual_components_test

        # Mock transcript tool
        mock_transcript_instance = mock_transcript_tool.return_value
        mock_transcript_instance._run.return_value = "Test transcript content"

        # Mock blog tool
        mock_blog_instance = mock_blog_tool.return_value
        mock_blog_instance._run.return_value = "Generated blog content"

        result = individual_components_test('https://youtube.com/watch?v=test123')

        assert result == "Generated blog content"
        mock_transcript_instance._run.assert_called_once()
        mock_blog_instance._run.assert_called_once()

    @patch('app.services.youtube_service.YouTubeTranscriptTool')
    def test_individual_components_test_transcript_error(self, mock_transcript_tool):
        """Test individual components test with transcript error"""
        from app.services.blog_service import individual_components_test

        mock_transcript_instance = mock_transcript_tool.return_value
        mock_transcript_instance._run.return_value = "ERROR: Transcript failed"

        result = individual_components_test('https://youtube.com/watch?v=test123')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'ERROR: Transcript failed' in result

    @patch('app.services.youtube_service.YouTubeTranscriptTool')
    @patch('app.services.blog_service.BlogGeneratorTool')
    def test_individual_components_test_blog_error(self, mock_blog_tool, mock_transcript_tool):
        """Test individual components test with blog generation error"""
        from app.services.blog_service import individual_components_test

        mock_transcript_instance = mock_transcript_tool.return_value
        mock_transcript_instance._run.return_value = "Test transcript content"

        mock_blog_instance = mock_blog_tool.return_value
        mock_blog_instance._run.return_value = "ERROR: Blog generation failed"

        result = individual_components_test('https://youtube.com/watch?v=test123')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'ERROR: Blog generation failed' in result

    @patch('app.services.youtube_service.YouTubeTranscriptTool')
    def test_individual_components_test_exception(self, mock_transcript_tool):
        """Test individual components test with exception"""
        from app.services.blog_service import individual_components_test

        mock_transcript_tool.side_effect = Exception("Component test error")

        result = individual_components_test('https://youtube.com/watch?v=test123')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'Component test failed: Component test error' in result

    def test_extract_video_id_standard_url(self):
        """Test video ID extraction from standard YouTube URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://youtube.com/watch?v=dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    def test_extract_video_id_short_url(self):
        """Test video ID extraction from short YouTube URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://youtu.be/dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    def test_extract_video_id_embed_url(self):
        """Test video ID extraction from embed YouTube URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://youtube.com/embed/dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    def test_extract_video_id_shorts_url(self):
        """Test video ID extraction from YouTube Shorts URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://youtube.com/shorts/dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    def test_extract_video_id_mobile_url(self):
        """Test video ID extraction from mobile YouTube URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://m.youtube.com/watch?v=dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    def test_extract_video_id_live_url(self):
        """Test video ID extraction from YouTube Live URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://youtube.com/live/dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    def test_extract_video_id_invalid_url(self):
        """Test video ID extraction from invalid URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://invalid-url.com')
        assert video_id is None

    def test_extract_video_id_empty_url(self):
        """Test video ID extraction from empty URL"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('')
        assert video_id is None

    def test_extract_video_id_invalid_format(self):
        """Test video ID extraction with invalid video ID format"""
        from app.services.blog_service import _extract_video_id

        video_id = _extract_video_id('https://youtube.com/watch?v=invalid')
        assert video_id is None

    def test_clean_final_output_basic(self):
        """Test basic final output cleaning"""
        from app.services.blog_service import _clean_final_output

        input_content = """
        Action: BlogGeneratorTool
        Tool: YouTubeTranscriptTool
        BlogGeneratorTool executed
        YouTubeTranscriptTool processed

        # Main Heading

        Content here
        """

        result = _clean_final_output(input_content)

        assert 'Action:' not in result
        assert 'Tool:' not in result
        assert 'BlogGeneratorTool' not in result
        assert 'YouTubeTranscriptTool' not in result
        assert '# Main Heading' in result

    def test_clean_final_output_json_artifacts(self):
        """Test cleaning JSON artifacts from final output"""
        from app.services.blog_service import _clean_final_output

        input_content = """
        {"key": "value"}
        {invalid json}
        { "another": "object" }

        # Heading
        Content here
        """

        result = _clean_final_output(input_content)

        assert '{"key": "value"}' not in result
        assert '{invalid json}' not in result
        assert '# Heading' in result

    def test_clean_final_output_markdown_artifacts(self):
        """Test cleaning markdown artifacts from final output"""
        from app.services.blog_service import _clean_final_output

        input_content = """
        ***excessive asterisks***
        ---horizontal rule---
        ||pipe symbols||
        ___underscores___

        # Heading
        Content here
        """

        result = _clean_final_output(input_content)

        assert '***' not in result
        assert '---' not in result
        assert '||' not in result
        assert '___' not in result
        assert '# Heading' in result

    def test_clean_final_output_list_formatting(self):
        """Test cleaning and fixing list formatting"""
        from app.services.blog_service import _clean_final_output

        input_content = """
        • bullet point
        * asterisk point
        1.numbered item

        # Heading
        """

        result = _clean_final_output(input_content)

        assert '- bullet point' in result
        assert '- asterisk point' in result
        assert '1. numbered item' in result or '1.numbered item' in result

    def test_clean_final_output_empty_content(self):
        """Test cleaning empty content"""
        from app.services.blog_service import _clean_final_output

        result = _clean_final_output('')
        assert result == ''

    def test_create_error_response(self):
        """Test error response creation"""
        from app.services.blog_service import _create_error_response

        result = _create_error_response('https://youtube.com/watch?v=test', 'Test error message')

        assert '# YouTube Video Analysis - Technical Issue' in result
        assert 'https://youtube.com/watch?v=test' in result
        assert 'Test error message' in result
        assert 'Troubleshooting Steps' in result
        assert 'Alternative Approaches' in result


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
