import logging
from unittest.mock import patch
from crewai import Agent
from src.agent import create_agents
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool


def test_create_agents_returns_two_agents():
    """Ensure create_agents returns two Agent instances"""
    transcriber, writer = create_agents()
    assert isinstance(transcriber, Agent)
    assert isinstance(writer, Agent)


def test_transcriber_agent_properties():
    """Check attributes of the transcriber agent"""
    transcriber, _ = create_agents()
    
    assert transcriber.role == 'YouTube Technical Content Extractor'
    assert "capture every specific detail" in transcriber.backstory
    assert isinstance(transcriber.tools[0], YouTubeTranscriptTool)
    assert transcriber.verbose is True
    assert callable(transcriber.step_callback)


def test_writer_agent_properties():
    """Check attributes of the writer agent"""
    _, writer = create_agents()

    assert writer.role == 'Technical Blog Writer'
    assert "preserve every tool name" in writer.backstory
    assert isinstance(writer.tools[0], BlogGeneratorTool)
    assert writer.verbose is True
    assert callable(writer.step_callback)


def test_step_callbacks_trigger_log_messages(caplog):
    """Test that step callbacks log messages correctly"""
    caplog.set_level(logging.INFO)

    transcriber, writer = create_agents()

    # Manually trigger the callbacks
    transcriber.step_callback("dummy_step_1")
    writer.step_callback("dummy_step_2")

    assert "Transcriber step completed" in caplog.text
    assert "Writer step completed" in caplog.text


def test_logger_info_called_on_creation():
    """Verify logger.info is called when agents are created"""
    with patch('src.agent.logger.info') as mock_log:
        create_agents()
        mock_log.assert_called_with("Enhanced agents created successfully")

def test_full_logger_coverage():
    with patch('src.agent.logger.info') as mock_log:
        transcriber, writer = create_agents()
        transcriber.step_callback("step_1")
        writer.step_callback("step_2")

        mock_log.assert_any_call("Enhanced agents created successfully")
        mock_log.assert_any_call("Transcriber step completed")
        mock_log.assert_any_call("Writer step completed")
