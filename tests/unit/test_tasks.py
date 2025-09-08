import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from crewai import Task
from src.task import create_tasks


class TestCreateTasks:
    """Comprehensive test cases for create_tasks function"""

    def setup_method(self):
        """Setup method to initialize test data"""
        self.transcriber = Mock()
        self.writer = Mock()
        self.youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.language = "en"

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_success(self, mock_task_class, mock_logger):
        """Test successful task creation with all components"""
        # Setup mocks
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        result = create_tasks(
            self.transcriber, self.writer, self.youtube_url, self.language
        )

        # Verify return values
        assert result == (mock_transcript_task, mock_blog_task)
        assert len(result) == 2

        # Verify Task constructor calls
        assert mock_task_class.call_count == 2

        # Verify logger call
        mock_logger.info.assert_called_once_with("Enhanced tasks created successfully")

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_transcript_task_configuration(
        self, mock_task_class, mock_logger
    ):
        """Test transcript task configuration parameters"""
        # Setup mocks
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Verify first Task call (transcript_task)
        first_call = mock_task_class.call_args_list[0]
        call_kwargs = first_call[1]

        # Check description content
        description = call_kwargs["description"]
        assert self.youtube_url in description
        assert self.language in description
        assert "Extract the complete, detailed transcript" in description
        assert "CRITICAL: Preserve ALL specific tool names" in description
        assert "company names, technical terms, version numbers" in description
        assert "If extraction fails, provide a clear error message" in description

        # Check expected_output content
        expected_output = call_kwargs["expected_output"]
        assert "Complete transcript with ALL specific tool names" in expected_output
        assert "technical details, company names, version numbers" in expected_output
        assert "If extraction fails, provide ERROR:" in expected_output

        # Check agent assignment
        assert call_kwargs["agent"] == self.transcriber

        # Check callback exists
        assert "callback" in call_kwargs
        assert callable(call_kwargs["callback"])

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_blog_task_configuration(self, mock_task_class, mock_logger):
        """Test blog task configuration parameters"""
        # Setup mocks
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Verify second Task call (blog_task)
        second_call = mock_task_class.call_args_list[1]
        call_kwargs = second_call[1]

        # Check description content
        description = call_kwargs["description"]
        assert "Create a comprehensive, detailed blog article" in description
        assert "CRITICAL REQUIREMENTS:" in description
        assert "If the input starts with 'ERROR:'" in description
        assert "PRESERVE ALL SPECIFIC INFORMATION:" in description
        assert "Include EVERY tool name, company name" in description
        assert "Preserve all specific recommendations" in description
        assert "Include exact version numbers" in description
        assert "Fabric wins AI category" in description
        assert "FORMAT: Use the exact categories" in description

        # Check expected_output content
        expected_output = call_kwargs["expected_output"]
        assert "Detailed blog article that reads like" in expected_output
        assert "preserving every specific tool name" in expected_output
        assert "technical detail, comparison" in expected_output
        assert "OR: Informative article about the video" in expected_output

        # Check agent assignment
        assert call_kwargs["agent"] == self.writer

        # Check context assignment
        assert call_kwargs["context"] == [mock_transcript_task]

        # Check callback exists
        assert "callback" in call_kwargs
        assert callable(call_kwargs["callback"])

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_with_different_language(self, mock_task_class, mock_logger):
        """Test task creation with different language parameter"""
        # Setup
        language = "es"
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, language)

        # Verify language is included in description
        first_call = mock_task_class.call_args_list[0]
        description = first_call[1]["description"]
        assert f"Language: {language}" in description

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_with_different_youtube_url(
        self, mock_task_class, mock_logger
    ):
        """Test task creation with different YouTube URL"""
        # Setup
        different_url = "https://www.youtube.com/watch?v=abcdef12345"
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, different_url, self.language)

        # Verify URL is included in description
        first_call = mock_task_class.call_args_list[0]
        description = first_call[1]["description"]
        assert different_url in description

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_transcript_task_callback_with_output(self, mock_task_class, mock_logger):
        """Test transcript task callback with task output"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get the callback from first task
        callback = mock_task_class.call_args_list[0][1]["callback"]

        # Setup mock task with output
        mock_task = Mock()
        mock_task.output = "This is a sample transcript output that is longer than 100 characters to test the truncation feature"

        # Execute callback
        callback(mock_task)

        # Verify logger call with truncated output
        expected_message = f"Transcript task completed: {mock_task.output[:100]}..."
        mock_logger.info.assert_any_call(expected_message)

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_transcript_task_callback_without_output(
        self, mock_task_class, mock_logger
    ):
        """Test transcript task callback without task output"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get the callback from first task
        callback = mock_task_class.call_args_list[0][1]["callback"]

        # Setup mock task without output
        mock_task = Mock()
        mock_task.output = None

        # Execute callback
        callback(mock_task)

        # Verify logger call with 'No output' message
        expected_message = "Transcript task completed: No output..."
        mock_logger.info.assert_any_call(expected_message)

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_transcript_task_callback_with_empty_output(
        self, mock_task_class, mock_logger
    ):
        """Test transcript task callback with empty output"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get the callback from first task
        callback = mock_task_class.call_args_list[0][1]["callback"]

        # Setup mock task with empty output
        mock_task = Mock()
        mock_task.output = ""

        # Execute callback
        callback(mock_task)

        # Verify logger call with 'No output' message
        expected_message = "Transcript task completed: No output..."
        mock_logger.info.assert_any_call(expected_message)

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_blog_task_callback_with_output(self, mock_task_class, mock_logger):
        """Test blog task callback with task output"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get the callback from second task
        callback = mock_task_class.call_args_list[1][1]["callback"]

        # Setup mock task with output
        mock_task = Mock()
        mock_task.output = "This is a sample blog output with multiple characters"

        # Execute callback
        callback(mock_task)

        # Verify logger call with character count
        expected_message = f"Blog task completed: {len(mock_task.output)} characters"
        mock_logger.info.assert_any_call(expected_message)

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_blog_task_callback_without_output(self, mock_task_class, mock_logger):
        """Test blog task callback without task output"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get the callback from second task
        callback = mock_task_class.call_args_list[1][1]["callback"]

        # Setup mock task without output
        mock_task = Mock()
        mock_task.output = None

        # Execute callback
        callback(mock_task)

        # Verify logger call with 0 characters
        expected_message = "Blog task completed: 0 characters"
        mock_logger.info.assert_any_call(expected_message)

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_blog_task_callback_with_empty_output(self, mock_task_class, mock_logger):
        """Test blog task callback with empty output"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get the callback from second task
        callback = mock_task_class.call_args_list[1][1]["callback"]

        # Setup mock task with empty output
        mock_task = Mock()
        mock_task.output = ""

        # Execute callback
        callback(mock_task)

        # Verify logger call with 0 characters
        expected_message = "Blog task completed: 0 characters"
        mock_logger.info.assert_any_call(expected_message)

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_with_none_agents(self, mock_task_class, mock_logger):
        """Test task creation with None agents"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(None, None, self.youtube_url, self.language)

        # Verify None agents are passed correctly
        first_call = mock_task_class.call_args_list[0]
        assert first_call[1]["agent"] is None

        second_call = mock_task_class.call_args_list[1]
        assert second_call[1]["agent"] is None

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_with_mock_agents(self, mock_task_class, mock_logger):
        """Test task creation with mock agents having attributes"""
        # Setup
        transcriber_with_attrs = Mock()
        transcriber_with_attrs.role = "Transcriber"
        transcriber_with_attrs.goal = "Extract transcripts"

        writer_with_attrs = Mock()
        writer_with_attrs.role = "Writer"
        writer_with_attrs.goal = "Write blogs"

        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(
            transcriber_with_attrs, writer_with_attrs, self.youtube_url, self.language
        )

        # Verify agents are passed correctly
        first_call = mock_task_class.call_args_list[0]
        assert first_call[1]["agent"] == transcriber_with_attrs

        second_call = mock_task_class.call_args_list[1]
        assert second_call[1]["agent"] == writer_with_attrs

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_with_long_youtube_url(self, mock_task_class, mock_logger):
        """Test task creation with very long YouTube URL"""
        # Setup
        long_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123s&list=PLrSoUrWBcWer1234567890abcdef&index=1"
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, long_url, self.language)

        # Verify URL is included in description
        first_call = mock_task_class.call_args_list[0]
        description = first_call[1]["description"]
        assert long_url in description

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_with_special_characters_in_language(
        self, mock_task_class, mock_logger
    ):
        """Test task creation with special characters in language"""
        # Setup
        special_language = "zh-CN"
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, special_language)

        # Verify language is included in description
        first_call = mock_task_class.call_args_list[0]
        description = first_call[1]["description"]
        assert f"Language: {special_language}" in description

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_verifies_task_context_dependency(
        self, mock_task_class, mock_logger
    ):
        """Test that blog task depends on transcript task"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Verify that blog_task context includes transcript_task
        second_call = mock_task_class.call_args_list[1]
        context = second_call[1]["context"]
        assert context == [mock_transcript_task]

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_logger_module_name(self, mock_task_class, mock_logger):
        """Test that logger is created with correct module name"""
        # This test ensures the logger is properly initialized
        # The actual logger creation is tested by verifying the info call

        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Verify logger info was called
        mock_logger.info.assert_called_once_with("Enhanced tasks created successfully")

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_callback_lambda_functionality(
        self, mock_task_class, mock_logger
    ):
        """Test that callback lambda functions work correctly"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        # Get callbacks
        transcript_callback = mock_task_class.call_args_list[0][1]["callback"]
        blog_callback = mock_task_class.call_args_list[1][1]["callback"]

        # Test that callbacks are lambda functions
        assert callable(transcript_callback)
        assert callable(blog_callback)

        # Test callback names (lambda functions have '<lambda>' as __name__)
        assert transcript_callback.__name__ == "<lambda>"
        assert blog_callback.__name__ == "<lambda>"

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_exception_handling(self, mock_task_class, mock_logger):
        """Test behavior when Task creation raises an exception"""
        # Setup
        mock_task_class.side_effect = Exception("Task creation failed")

        # Execute and verify exception is raised
        with pytest.raises(Exception) as exc_info:
            create_tasks(self.transcriber, self.writer, self.youtube_url, self.language)

        assert str(exc_info.value) == "Task creation failed"

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_function_docstring(self, mock_task_class, mock_logger):
        """Test that the function has the correct docstring"""
        # Verify function docstring
        assert (
            create_tasks.__doc__
            == "Create enhanced tasks with better error handling and validation"
        )

    @patch("src.task.logger")
    @patch("src.task.Task")
    def test_create_tasks_return_type(self, mock_task_class, mock_logger):
        """Test that function returns correct types"""
        # Setup
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        result = create_tasks(
            self.transcriber, self.writer, self.youtube_url, self.language
        )

        # Verify return type is tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

        # Verify tuple contents
        transcript_task, blog_task = result
        assert transcript_task == mock_transcript_task
        assert blog_task == mock_blog_task
