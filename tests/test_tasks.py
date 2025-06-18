from src.task import create_tasks
from crewai import Agent
from unittest.mock import MagicMock

def test_task_creation():
    # Create proper Agent instances instead of MagicMock
    transcriber = Agent(
        role='Test Transcriber',
        goal='Test goal',
        backstory='Test backstory',
        tools=[],
        verbose=True
    )
    
    writer = Agent(
        role='Test Writer',
        goal='Test goal',
        backstory='Test backstory',
        tools=[],
        verbose=True
    )
    
    transcript_task, blog_task = create_tasks(transcriber, writer)
    
    assert "youtube_url" in transcript_task.description
    assert transcript_task.agent == transcriber
    assert blog_task.context == [transcript_task]