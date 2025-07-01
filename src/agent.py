from crewai import Agent
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool

def create_agents():
    transcriber = Agent(
        role='YouTube Video Transcriber',
        goal='Extract accurate transcripts from YouTube videos using multiple methods',
        backstory=(
            'You are an expert at extracting video transcripts from YouTube videos. '
            'You use the youtube-transcript-api as your primary method, and you always '
            'verify that the content you extract is meaningful and related to the video.'
        ),
        tools=[YouTubeTranscriptTool()],
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    writer = Agent(
        role='Blog Content Writer',
        goal='Transform video transcripts into engaging, well-structured blog articles',
        backstory=(
            'You are a professional content writer who specializes in creating '
            'comprehensive blog articles from video transcripts. You ensure that '
            'your articles are well-structured, engaging, and capture all the key '
            'insights from the original video content.'
        ),
        tools=[BlogGeneratorTool()],
        verbose=True,
        memory=True,
        allow_delegation=False
    )
    
    return transcriber, writer