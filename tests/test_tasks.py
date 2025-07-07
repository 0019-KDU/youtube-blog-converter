import logging
from unittest.mock import patch, MagicMock
from src.task import create_tasks
from src.agent import create_agents
from crewai import Task


def test_create_tasks_basic_properties():
    transcriber, writer = create_agents()
    youtube_url = "https://www.youtube.com/watch?v=test123"
    language = "en"
    
    transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
    
    # Check types
    assert isinstance(transcript_task, Task)
    assert isinstance(blog_task, Task)

    # Check descriptions contain expected phrases and input values
    assert youtube_url in transcript_task.description
    assert "Preserve ALL specific tool names" in transcript_task.description

    assert "PRESERVE ALL SPECIFIC INFORMATION" in blog_task.description
    assert "FORMAT: Use the exact categories" in blog_task.description

    # blog_task should depend on transcript_task
    assert blog_task.context == [transcript_task]


def test_create_tasks_logging_called():
    transcriber, writer = create_agents()
    youtube_url = "https://www.youtube.com/watch?v=test123"
    language = "en"
    
    with patch('src.task.logger.info') as mock_log:
        create_tasks(transcriber, writer, youtube_url, language)
        mock_log.assert_called_with("Enhanced tasks created successfully")


def test_transcript_task_callback_logs_output(caplog):
    transcriber, writer = create_agents()
    youtube_url = "https://www.youtube.com/watch?v=test123"
    language = "en"
    
    transcript_task, _ = create_tasks(transcriber, writer, youtube_url, language)

    # Set log level to INFO so logs are captured
    caplog.set_level(logging.INFO)

    # Simulate task output set and trigger callback
    transcript_task.output = "This is a transcript output example..."
    transcript_task.callback(transcript_task)
    
    assert "Transcript task completed: This is a transcript output example..." in caplog.text

    # Also test with no output set
    transcript_task.output = None
    transcript_task.callback(transcript_task)
    assert "Transcript task completed: No output..." in caplog.text


def test_blog_task_callback_logs_output_length(caplog):
    transcriber, writer = create_agents()
    youtube_url = "https://www.youtube.com/watch?v=test123"
    language = "en"
    
    _, blog_task = create_tasks(transcriber, writer, youtube_url, language)
    
    caplog.set_level(logging.INFO)
    
    # Set output with some length and trigger callback
    blog_task.output = "This is a blog article content with more than 50 chars..."
    blog_task.callback(blog_task)
    
    assert "Blog task completed: " in caplog.text
    assert "characters" in caplog.text
    
    # Test empty output
    blog_task.output = None
    blog_task.callback(blog_task)
    assert "Blog task completed: 0 characters" in caplog.text


def test_create_tasks_empty_url_and_language():
    """Test edge case with empty YouTube URL and language"""
    transcriber, writer = create_agents()
    youtube_url = ""
    language = ""
    
    transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)

    assert "https://" not in transcript_task.description  # no URL
    assert "Language: " in transcript_task.description  # should still contain Language key, even if empty

    # Should still create blog task with context linking
    assert blog_task.context == [transcript_task]


def test_create_tasks_callbacks_are_callable():
    """Ensure callback functions are callable"""
    transcriber, writer = create_agents()
    youtube_url = "https://www.youtube.com/watch?v=test123"
    language = "en"
    
    transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
    
    assert callable(transcript_task.callback)
    assert callable(blog_task.callback)
