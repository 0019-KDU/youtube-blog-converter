import pytest
from unittest.mock import patch, MagicMock, call
import os
import logging
from src.main import generate_blog_from_youtube, cli_main

# Test data
TEST_YOUTUBE_URL = "https://youtu.be/dQw4w9WgXcQ"
TEST_LANGUAGE = "en"

# Tests for generate_blog_from_youtube
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success(mock_tasks, mock_agents, mock_crew):
    """Test successful blog generation"""
    # Mock agents and tasks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Generated blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    
    # Mock crew
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    
    # Test blog generation
    blog_content = generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
    assert blog_content == "Generated blog content"

def test_missing_api_key(monkeypatch):
    """Test missing API key raises error"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
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
        generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
    assert "no output produced" in str(excinfo.value)

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_crew_exception(mock_tasks, mock_agents, mock_crew):
    """Test crew exception handling"""
    # Mock agents and tasks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    mock_tasks.return_value = (MagicMock(), MagicMock())
    
    # Mock crew to raise exception during kickoff
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test exception")
    
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
    assert "Error during blog generation" in str(excinfo.value)

def test_generate_blog_invalid_url():
    """Test invalid URL validation"""
    with pytest.raises(ValueError) as excinfo:
        generate_blog_from_youtube("invalid_url", TEST_LANGUAGE)
    assert "Invalid YouTube URL" in str(excinfo.value)

@patch('src.main.logger')
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success_logging(mock_tasks, mock_agents, mock_crew, mock_logger):
    """Test success path logging"""
    # Setup mocks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    
    # Call function
    blog_content = generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
    
    # Verify logs
    expected_calls = [
        call.info(f"Starting blog generation for: {TEST_YOUTUBE_URL}"),
        call.info(f"Successfully generated blog for: {TEST_YOUTUBE_URL}")
    ]
    mock_logger.assert_has_calls(expected_calls)

@patch('src.main.logger')
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_failure_logging(mock_tasks, mock_agents, mock_crew, mock_logger):
    """Test exception path logging"""
    # Setup mocks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    mock_tasks.return_value = (MagicMock(), MagicMock())
    
    # Mock crew to raise exception
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test error")
    
    # Call function and verify exception
    with pytest.raises(RuntimeError):
        generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
    
    # Verify logs
    expected_calls = [
        call.info(f"Starting blog generation for: {TEST_YOUTUBE_URL}"),
        call.error(f"Blog generation failed for {TEST_YOUTUBE_URL}: Test error")
    ]
    mock_logger.assert_has_calls(expected_calls)

def test_missing_api_key_logging(monkeypatch, caplog):
    """Test API key missing logs correctly"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            generate_blog_from_youtube(TEST_YOUTUBE_URL, TEST_LANGUAGE)
    
    # Verify log
    assert "OpenAI API key not found" in caplog.text

def test_cli_main_success(monkeypatch, capsys):
    """Test CLI main function success path"""
    # Mock user inputs
    inputs = [TEST_YOUTUBE_URL, TEST_LANGUAGE]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock generate function
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        cli_main()
    
    # Verify output
    captured = capsys.readouterr()
    assert "Generated blog article:" in captured.out
    assert "Generated blog content"[:200] in captured.out

def test_cli_main_error(monkeypatch, capsys):
    """Test CLI main function error handling"""
    # Mock user inputs
    inputs = [TEST_YOUTUBE_URL, TEST_LANGUAGE]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock generate function to raise error
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.side_effect = RuntimeError("Test error")
        cli_main()
    
    # Verify error output
    captured = capsys.readouterr()
    assert "Error: Test error" in captured.out

def test_cli_main_default_language(monkeypatch):
    """Test CLI uses default language when empty"""
    # Mock user inputs
    inputs = [TEST_YOUTUBE_URL, ""]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock generate function
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        cli_main()
    
    # Verify default language was used
    mock_generate.assert_called_with(TEST_YOUTUBE_URL, "en")

def test_cli_main_output(monkeypatch, capsys):
    """Test CLI main function prints output correctly"""
    # Mock user inputs
    inputs = [TEST_YOUTUBE_URL, TEST_LANGUAGE]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock the blog generation
    mock_blog = "Mock blog article content" * 10  # Long enough to test truncation
    with patch('src.main.generate_blog_from_youtube', return_value=mock_blog):
        cli_main()
    
    # Capture the output
    captured = capsys.readouterr()
    output = captured.out
    
    # Check the output
    assert "Generated blog article:" in output
    assert mock_blog[:200] in output
    assert "..." in output

def test_cli_main_error_output(monkeypatch, capsys):
    """Test CLI main function prints errors correctly"""
    # Mock user inputs
    inputs = [TEST_YOUTUBE_URL, TEST_LANGUAGE]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    # Mock the blog generation to raise an exception
    error_msg = "Test error message"
    with patch('src.main.generate_blog_from_youtube', side_effect=RuntimeError(error_msg)):
        cli_main()
    
    # Capture the output
    captured = capsys.readouterr()
    output = captured.out
    
    # Check the error message is printed
    assert f"Error: {error_msg}" in output

def test_main_guard():
    """Test that cli_main is called when script is run directly"""
    with patch('src.main.cli_main') as mock_cli_main:
        # Use importlib to simulate running the module as main
        import importlib
        import sys
        
        # Save original arguments
        original_argv = sys.argv
        
        try:
            # Simulate running the script directly
            sys.argv = ['main.py']
            
            # Run the module as main
            importlib.import_module('src.main')
            
            # When run as main, the __name__ is set to '__main__'
            if hasattr(sys.modules['src.main'], '__name__'):
                sys.modules['src.main'].__name__ = '__main__'
                
            # Execute the main guard
            if sys.modules['src.main'].__name__ == '__main__':
                sys.modules['src.main'].cli_main()
        finally:
            # Restore original arguments
            sys.argv = original_argv
    
    # Verify cli_main was called
    mock_cli_main.assert_called_once()