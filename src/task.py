# src/task.py
from crewai import Task

def create_tasks(transcriber, writer, youtube_url, language):
    transcript_task = Task(
        description=(
            f"Extract the complete transcript from this YouTube video: {youtube_url}. "
            f"Use language: {language}. Make sure to get the full content and verify "
            "that it contains meaningful dialogue or narration from the video."
        ),
        expected_output=(
            'A complete, accurate transcript of the YouTube video content that contains '
            'the actual spoken words from the video, properly formatted and cleaned up.'
        ),
        agent=transcriber
    )

    blog_task = Task(
        description=(
            "Using the transcript provided, create a comprehensive blog article that: "
            "1. Has an engaging title based on the video content "
            "2. Includes a brief introduction explaining what the video covers "
            "3. Breaks down the main topics discussed in the video into clear sections "
            "4. Provides detailed explanations of key concepts mentioned "
            "5. Includes relevant examples or insights from the transcript "
            "6. Ends with a conclusion that summarizes the main takeaways "
            "7. Is formatted in Markdown with proper headings and structure "
            "8. References the original video content throughout "
            "Make sure the article is substantial (at least 800 words) and engaging."
        ),
        expected_output=(
            'A well-structured, comprehensive blog article in Markdown format that '
            'thoroughly covers all the main topics from the video transcript, with '
            'clear headings, detailed explanations, and engaging content.'
        ),
        agent=writer,
        context=[transcript_task]
    )
    
    return transcript_task, blog_task