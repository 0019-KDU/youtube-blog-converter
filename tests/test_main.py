# tests/test_main.py
import pytest
from unittest.mock import patch, MagicMock
import os
import logging
from src.main import generate_blog_from_youtube, cli_main
from unittest.mock import call

TEST_YOUTUBE_URL = "https://youtu.be/dQw4w9WgXcQ"

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success(mock_tasks, mock_agents, mock_crew):
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Generated blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    
    blog_content = generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    assert blog_content == "Generated blog content"

def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    assert "OpenAI API key not found" in str(excinfo.value)

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_no_output(mock_tasks, mock_agents, mock_crew):
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    
    mock_blog_task = MagicMock()
    mock_blog_task.output = None
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    assert "no output produced" in str(excinfo.value)

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_crew_exception(mock_tasks, mock_agents, mock_crew):
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    mock_tasks.return_value = (MagicMock(), MagicMock())
    
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test exception")
    
    with pytest.raises(RuntimeError) as excinfo:
        generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    assert "Error during blog generation" in str(excinfo.value)

def test_generate_blog_invalid_url():
    with pytest.raises(ValueError) as excinfo:
        generate_blog_from_youtube("invalid_url", "en")
    assert "Invalid YouTube URL" in str(excinfo.value)

@patch('src.main.logger')
@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success_logging(mock_tasks, mock_agents, mock_crew, mock_logger):
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    
    blog_content = generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    
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
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    mock_tasks.return_value = (MagicMock(), MagicMock())
    
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.side_effect = Exception("Test error")
    
    with pytest.raises(RuntimeError):
        generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    
    expected_calls = [
        call.info(f"Starting blog generation for: {TEST_YOUTUBE_URL}"),
        call.error(f"Blog generation failed for {TEST_YOUTUBE_URL}: Test error")
    ]
    mock_logger.assert_has_calls(expected_calls)

def test_missing_api_key_logging(monkeypatch, caplog):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            generate_blog_from_youtube(TEST_YOUTUBE_URL, "en")
    
    assert "OpenAI API key not found" in caplog.text

def test_cli_main_success(monkeypatch, capsys):
    inputs = [TEST_YOUTUBE_URL, "en"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        cli_main()
    
    captured = capsys.readouterr()
    assert "Generated blog article:" in captured.out
    assert "Generated blog content"[:200] in captured.out

def test_cli_main_error(monkeypatch, capsys):
    inputs = [TEST_YOUTUBE_URL, "en"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.side_effect = RuntimeError("Test error")
        cli_main()
    
    captured = capsys.readouterr()
    assert "Error: Test error" in captured.out

def test_cli_main_default_language(monkeypatch):
    inputs = [TEST_YOUTUBE_URL, ""]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    with patch('src.main.generate_blog_from_youtube') as mock_generate:
        mock_generate.return_value = "Generated blog content"
        cli_main()
    
    mock_generate.assert_called_with(TEST_YOUTUBE_URL, "en")

def test_cli_main_output(monkeypatch, capsys):
    inputs = [TEST_YOUTUBE_URL, "en"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    mock_blog = "Mock blog article content" * 10
    with patch('src.main.generate_blog_from_youtube', return_value=mock_blog):
        cli_main()
    
    captured = capsys.readouterr()
    output = captured.out
    assert "Generated blog article:" in output
    assert mock_blog[:200] in output
    assert "..." in output

def test_cli_main_error_output(monkeypatch, capsys):
    inputs = [TEST_YOUTUBE_URL, "en"]
    monkeypatch.setattr('builtins.input', lambda _: inputs.pop(0))
    
    error_msg = "Test error message"
    with patch('src.main.generate_blog_from_youtube', side_effect=RuntimeError(error_msg)):
        cli_main()
    
    captured = capsys.readouterr()
    output = captured.out
    assert f"Error: {error_msg}" in output

def test_main_guard():
    with patch('src.main.cli_main') as mock_cli_main:
        import importlib
        import sys
        
        original_argv = sys.argv
        try:
            sys.argv = ['main.py']
            importlib.import_module('src.main')
            if hasattr(sys.modules['src.main'], '__name__'):
                sys.modules['src.main'].__name__ = '__main__'
            if sys.modules['src.main'].__name__ == '__main__':
                sys.modules['src.main'].cli_main()
        finally:
            sys.argv = original_argv
    
    mock_cli_main.assert_called_once()