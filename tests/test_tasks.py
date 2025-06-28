# tests/test_tasks.py
from src.task import create_tasks
from crewai import Agent
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool

def test_task_creation():
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
    
    youtube_url = "https://youtu.be/dQw4w9WgXcQ"
    language = "en"
    
    transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
    
    assert youtube_url in transcript_task.description
    assert language in transcript_task.description
    assert transcript_task.expected_output == 'A single string containing the entire video transcript.'
    assert transcript_task.agent == transcriber
    assert isinstance(transcript_task.tools[0], YouTubeTranscriptTool)
    
    assert blog_task.description == 'Generate a blog article based on the retrieved transcript.'
    assert blog_task.expected_output == 'A well-structured blog article derived from the transcript.'
    assert blog_task.agent == writer
    assert isinstance(blog_task.tools[0], BlogGeneratorTool)
    assert blog_task.context == [transcript_task]
    
    transcript_tool = transcript_task.tools[0]
    assert "Retrieve transcript from a YouTube video URL" in transcript_tool.description
    
    blog_tool = blog_task.tools[0]
    assert "Generate a blog article from a video transcript" in blog_tool.description