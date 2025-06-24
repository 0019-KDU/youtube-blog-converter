import pytest
from unittest.mock import patch, MagicMock, call
import os
import logging

# Import the function to test
from src.main import generate_blog_from_youtube

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success(mock_tasks, mock_agents, mock_crew):
    """Test successful blog generation"""
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
    """Test missing API key raises error"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube("https://youtube.com/test", "en")
    assert "OpenAI API key not found" in str(excinfo.value)

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_no_output(mock_tasks, mock_agents, mock_crew):
    """Test no output raises error"""
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
    """Test crew exception handling"""
    # Mock agents and tasks
    mock_agents.return_value = (MagicMock(), MagicMock())
    mock_tasks.return_value = (MagicMock(), MagicMock())

    # Mock crew to raise exception during kickoff
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test exception")

    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube("https://youtube.com/test", "en")
    assert "Error during blog generation" in str(excinfo.value)

def test_generate_blog_invalid_url():
    """Test invalid URL validation"""
    with pytest.raises(ValueError) as excinfo:
        generate_blog_from_youtube("invalid_url", "en")
    assert "Invalid YouTube URL" in str(excinfo.value)

@patch('src.main.logger')
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success_logging(mock_tasks, mock_agents, mock_crew, mock_logger):
    """Test success path logging"""
    # Setup mocks
    mock_agents.return_value = (MagicMock(), MagicMock())
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance

    # Call function
    blog_content = generate_blog_from_youtube("https://youtube.com/test", "en")
    
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
    """Test exception path logging"""
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

def test_missing_api_key_logging(monkeypatch, caplog):
    """Test API key missing logs correctly"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            generate_blog_from_youtube("https://youtube.com/test", "en")
    
    # Verify log
    assert "OpenAI API key not found" in caplog.text

def test_cli_main_success(monkeypatch, capsys):
    """Test CLI main function success path"""
    # Mock user inputs
    inputs = ["https://youtube.com/test", "en"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock generate function
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        from src.main import cli_main
        cli_main()
    
    # Verify output
    captured = capsys.readouterr()
    assert "Generated blog article:" in captured.out
    assert "Generated blog content"[:200] in captured.out

def test_cli_main_error(monkeypatch, capsys):
    """Test CLI main function error handling"""
    # Mock user inputs
    inputs = ["https://youtube.com/test", "en"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock generate function to raise error
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.side_effect = RuntimeError("Test error")
        from src.main import cli_main
        cli_main()
    
    # Verify error output
    captured = capsys.readouterr()
    assert "Error: Test error" in captured.out

def test_cli_main_default_language(monkeypatch, capsys):
    """Test CLI uses default language when empty"""
    # Mock user inputs
    inputs = ["https://youtube.com/test", ""]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock generate function
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        from src.main import cli_main
        cli_main()
    
    # Verify default language was used
    mock_generate.assert_called_with("https://youtube.com/test", "en")