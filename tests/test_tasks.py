from src.task import create_tasks
from crewai import Agent

def test_task_creation():
    # Create proper Agent instances
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
    
    # Provide dummy values for new parameters
    youtube_url = "https://youtu.be/dQw4w9WgXcQ"
    language = "en"
    
    transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
    
    # Updated assertions to check for actual values in description
    assert youtube_url in transcript_task.description
    assert language in transcript_task.description
    assert transcript_task.agent == transcriber
    assert blog_task.context == [transcript_task]