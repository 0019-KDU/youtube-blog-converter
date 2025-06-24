from crewai import Task
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool

def create_tasks(transcriber, writer, youtube_url, language):
    """Create and return task instances"""
    transcript_task = Task(
        description=f'Retrieve the full transcript from the YouTube video at {youtube_url} in language {language}',
        expected_output='A single string containing the entire video transcript.',
        agent=transcriber,
        tools=[YouTubeTranscriptTool()]
    )

    blog_task = Task(
        description='Generate a blog article based on the retrieved transcript.',
        expected_output='A well-structured blog article derived from the transcript.',
        agent=writer,
        tools=[BlogGeneratorTool()],
        context=[transcript_task]
    )
    
    return transcript_task, blog_task