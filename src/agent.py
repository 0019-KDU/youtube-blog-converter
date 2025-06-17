from crewai import Agent
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool

def create_agents():
    """Create and return agent instances"""
    transcriber = Agent(
        role='Transcription Specialist',
        goal='Extract the transcript from the provided YouTube video URL',
        backstory='An expert in retrieving video transcripts efficiently.',
        tools=[YouTubeTranscriptTool()],
        verbose=True
    )

    writer = Agent(
        role='Blog Writer',
        goal='Write a detailed blog article from the video transcript',
        backstory='An expert content writer who converts raw transcripts into clear, SEO-friendly blogs.',
        tools=[BlogGeneratorTool()],
        verbose=True
    )
    
    return transcriber, writer