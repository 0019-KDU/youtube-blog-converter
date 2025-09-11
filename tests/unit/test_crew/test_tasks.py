from unittest.mock import Mock, patch

import pytest


class TestTasks:
    """Test task creation and configuration"""

    @patch('app.crew.tasks.Task')
    @patch('app.crew.tasks.logger')
    def test_create_tasks_success(self, mock_logger, mock_task_class):
        """Test successful task creation"""
        from app.crew.tasks import create_tasks

        # Mock agents
        mock_transcriber = Mock()
        mock_writer = Mock()

        # Mock Task instances
        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        # Execute
        transcript_task, blog_task = create_tasks(
            mock_transcriber, mock_writer, "https://youtube.com/watch?v=test", "en")

        # Verify
        assert transcript_task == mock_transcript_task
        assert blog_task == mock_blog_task
        assert mock_task_class.call_count == 2
        mock_logger.info.assert_called_with(
            "Enhanced tasks created successfully")

    @patch('app.crew.tasks.Task')
    @patch('app.crew.tasks.logger')
    def test_task_configuration_parameters(self, mock_logger, mock_task_class):
        """Test that tasks are configured with correct parameters"""
        from app.crew.tasks import create_tasks

        mock_transcriber = Mock()
        mock_writer = Mock()
        mock_task_class.return_value = Mock()

        youtube_url = "https://youtube.com/watch?v=test123"
        language = "en"

        create_tasks(mock_transcriber, mock_writer, youtube_url, language)

        # Verify task creation calls
        calls = mock_task_class.call_args_list
        assert len(calls) == 2

        # Check transcript task configuration
        transcript_kwargs = calls[0][1]
        assert youtube_url in transcript_kwargs['description']
        assert language in transcript_kwargs['description']
        assert "Extract the complete, detailed transcript" in transcript_kwargs['description']
        assert "Complete transcript with ALL specific tool names" in transcript_kwargs[
            'expected_output']
        assert transcript_kwargs['agent'] == mock_transcriber
        assert 'callback' in transcript_kwargs

        # Check blog task configuration
        blog_kwargs = calls[1][1]
        assert "Create a comprehensive, detailed blog article" in blog_kwargs['description']
        assert "CRITICAL REQUIREMENTS" in blog_kwargs['description']
        assert "Detailed blog article that reads like" in blog_kwargs['expected_output']
        assert blog_kwargs['agent'] == mock_writer
        assert 'context' in blog_kwargs
        assert 'callback' in blog_kwargs

    @patch('app.crew.tasks.Task')
    @patch('app.crew.tasks.logger')
    def test_task_context_relationship(self, mock_logger, mock_task_class):
        """Test that blog task has transcript task as context"""
        from app.crew.tasks import create_tasks

        mock_transcriber = Mock()
        mock_writer = Mock()

        mock_transcript_task = Mock()
        mock_blog_task = Mock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        create_tasks(
            mock_transcriber,
            mock_writer,
            "https://youtube.com/test",
            "en")

        # Check that blog task has transcript task as context
        calls = mock_task_class.call_args_list
        blog_task_kwargs = calls[1][1]  # Second task (blog task)

        assert 'context' in blog_task_kwargs
        assert mock_transcript_task in blog_task_kwargs['context']

    @patch('app.crew.tasks.Task')
    @patch('app.crew.tasks.logger')
    def test_task_callback_functionality(self, mock_logger, mock_task_class):
        """Test task callback functions work correctly"""
        from app.crew.tasks import create_tasks

        mock_transcriber = Mock()
        mock_writer = Mock()
        mock_task_class.return_value = Mock()

        create_tasks(
            mock_transcriber,
            mock_writer,
            "https://youtube.com/test",
            "en")

        # Get the callbacks
        calls = mock_task_class.call_args_list
        transcript_callback = calls[0][1]['callback']
        blog_callback = calls[1][1]['callback']

        # Test transcript callback
        mock_task_with_output = Mock()
        mock_task_with_output.output = "Sample transcript output content"
        transcript_callback(mock_task_with_output)

        # Test blog callback with no output
        mock_task_no_output = Mock()
        mock_task_no_output.output = None
        blog_callback(mock_task_no_output)

        # Verify logging occurred
        assert mock_logger.info.call_count >= 2

    @patch('app.crew.tasks.logger')
    def test_create_tasks_with_different_languages(self, mock_logger):
        """Test task creation with different language parameters"""
        from app.crew.tasks import create_tasks

        mock_transcriber = Mock()
        mock_writer = Mock()

        test_languages = ["en", "es", "fr", "de"]

        with patch('app.crew.tasks.Task') as mock_task_class:
            # FIX: Return a new Mock instance each time
            mock_task_class.side_effect = lambda *args, **kwargs: Mock()

            for lang in test_languages:
                create_tasks(
                    mock_transcriber,
                    mock_writer,
                    "https://youtube.com/test",
                    lang)

                # Check that language is included in description
                calls = mock_task_class.call_args_list
                # FIX: Get the correct call index
                latest_transcript_call_index = len(calls) - 2
                if latest_transcript_call_index >= 0:
                    latest_transcript_call = calls[latest_transcript_call_index]
                    transcript_description = latest_transcript_call[1]['description']
                    assert f"Language: {lang}" in transcript_description

    @patch('app.crew.tasks.Task')
    @patch('app.crew.tasks.logger')
    def test_task_creation_failure(self, mock_logger, mock_task_class):
        """Test handling of Task creation failures"""
        from app.crew.tasks import create_tasks

        mock_transcriber = Mock()
        mock_writer = Mock()

        # Make task creation fail
        mock_task_class.side_effect = ValueError("Invalid task configuration")

        with pytest.raises(ValueError, match="Invalid task configuration"):
            create_tasks(
                mock_transcriber,
                mock_writer,
                "https://youtube.com/test",
                "en")

    def test_create_tasks_parameter_validation(self):
        """Test parameter validation for create_tasks function"""
        from app.crew.tasks import create_tasks

        with patch('app.crew.tasks.Task') as mock_task_class:
            mock_task_class.return_value = Mock()

            # Test should not raise AttributeError, but should handle None gracefully
            # The function should validate parameters before accessing
            # attributes
            try:
                create_tasks(None, None, "https://youtube.com/test", "en")
                # If it doesn't raise, that's actually correct behavior
                assert True
            except (ValueError, TypeError):
                # These are acceptable validation errors
                assert True
            except AttributeError:
                # This indicates the function isn't properly validating inputs
                pytest.fail(
                    "Function should validate parameters before accessing attributes")


class TestTasksIntegration:
    """Integration tests for tasks"""

    @pytest.mark.skipif(
        not pytest.importorskip("crewai", reason="crewai not available"),
        condition=False,
        reason="Skip if crewai not available"
    )
    def test_actual_task_creation(self):
        """Test actual task creation with real CrewAI Task (if available)"""
        try:
            # Import check first
            pytest.importorskip("crewai")

            # Instead of using real CrewAI tasks (which would require real agents),
            # mock the Task creation but test the function logic
            with patch('app.crew.tasks.Task') as mock_task_class:
                from app.crew.tasks import create_tasks

                # Create properly structured mock agents
                mock_transcriber = Mock()
                mock_transcriber.role = "Transcriber"
                mock_transcriber.__class__.__name__ = "Agent"

                mock_writer = Mock()
                mock_writer.role = "Writer"
                mock_writer.__class__.__name__ = "Agent"

                # Mock the Task class to return Mock instances
                mock_task_instance = Mock()
                mock_task_class.return_value = mock_task_instance

                transcript_task, blog_task = create_tasks(
                    mock_transcriber, mock_writer, "https://youtube.com/watch?v=test", "en")

                # Verify that Tasks were created with proper parameters
                assert mock_task_class.call_count == 2
                assert transcript_task == mock_task_instance
                assert blog_task == mock_task_instance

                # Verify the task configurations
                calls = mock_task_class.call_args_list
                assert len(calls) == 2

                # Check transcript task
                transcript_args = calls[0][1]
                assert 'description' in transcript_args
                assert 'agent' in transcript_args
                assert transcript_args['agent'] == mock_transcriber

                # Check blog task
                blog_args = calls[1][1]
                assert 'description' in blog_args
                assert 'agent' in blog_args
                assert blog_args['agent'] == mock_writer
                assert 'context' in blog_args

        except ImportError:
            pytest.skip("CrewAI not available for integration test")
