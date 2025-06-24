from unittest.mock import patch, MagicMock , call
import pytest
from src.main import generate_blog_from_youtube
import logging

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success(mock_tasks, mock_agents, mock_crew):
    # Mock agents and tasks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)

    # Mock tasks
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Generated blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)

    # Mock crew
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.return_value = "Crew result"

    # Test blog generation
    blog_content = generate_blog_from_youtube("https://youtube.com/test", "en")
    assert blog_content == "Generated blog content"

def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube("https://youtube.com/test", "en")
    assert "OpenAI API key not found" in str(excinfo.value)

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_no_output(mock_tasks, mock_agents, mock_crew):
    # Mock agents and tasks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)

    # Mock tasks: blog_task has no output
    mock_blog_task = MagicMock()
    mock_blog_task.output = None
    mock_tasks.return_value = (MagicMock(), mock_blog_task)

    # Mock crew
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance

    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube("https://youtube.com/test", "en")
    assert "no output produced" in str(excinfo.value)

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_crew_exception(mock_tasks, mock_agents, mock_crew):
    # Mock agents and tasks
    mock_agents.return_value = (MagicMock(), MagicMock())
    mock_tasks.return_value = (MagicMock(), MagicMock())

    # Mock crew to raise exception during kickoff
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test exception")

    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube("https://youtube.com/test", "en")
    # Update the assertion to match the actual error message
    assert "Error during blog generation" in str(excinfo.value)  # Changed this line

def test_generate_blog_invalid_url():
    with pytest.raises(ValueError) as excinfo:
        generate_blog_from_youtube("invalid_url", "en")
    assert "Invalid YouTube URL" in str(excinfo.value)    

@patch('src.main.logger')
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success_logging(mock_tasks, mock_agents, mock_crew, mock_logger):
    """Test that success path logs correctly"""
    # Setup mocks
    mock_agents.return_value = (MagicMock(), MagicMock())
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance

    # Call function
    generate_blog_from_youtube("https://youtube.com/test", "en")
    
    # Verify logs
    expected_calls = [
        call.info("Starting blog generation for: https://youtube.com/test"),
        call.info("Successfully generated blog for: https://youtube.com/test")
    ]
    mock_logger.assert_has_calls(expected_calls)

@patch('src.main.logger')
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_failure_logging(mock_tasks, mock_agents, mock_crew, mock_logger):
    """Test that exception path logs correctly"""
    # Setup mocks
    mock_agents.return_value = (MagicMock(), MagicMock())
    mock_tasks.return_value = (MagicMock(), MagicMock())
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test error")
    
    # Call function and verify exception
    with pytest.raises(RuntimeError):
        generate_blog_from_youtube("https://youtube.com/test", "en")
    
    # Verify logs
    expected_calls = [
        call.info("Starting blog generation for: https://youtube.com/test"),
        call.error("Blog generation failed for https://youtube.com/test: Test error")
    ]
    mock_logger.assert_has_calls(expected_calls)    