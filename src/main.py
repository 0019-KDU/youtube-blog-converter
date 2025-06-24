import os
from dotenv import load_dotenv
from crewai import Crew, Process
import logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Use absolute imports
from src.agent import create_agents
from src.task import create_tasks

def generate_blog_from_youtube(youtube_url: str, language: str) -> str:
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OpenAI API key not found")
    
    # Input validation
    if not youtube_url or "youtube.com" not in youtube_url:
        raise ValueError("Invalid YouTube URL provided")
    
    logger.info(f"Starting blog generation for: {youtube_url}")  # Needs test coverage
    
    try:
        # Create agents and tasks
        transcriber, writer = create_agents(language)
        transcript_task, blog_task = create_tasks(youtube_url, transcriber, writer, language)
        
        # Form the crew
        crew = Crew(
            agents=[transcriber, writer],
            tasks=[transcript_task, blog_task],
            verbose=True
        )
        
        # Execute crew
        crew.kickoff()
        
        # Check if blog task produced output
        if blog_task.output is None:
            raise RuntimeError("Blog task completed but no output produced")
        
        blog_content = blog_task.output.raw
        logger.info(f"Successfully generated blog for: {youtube_url}")  # Needs test coverage
        return blog_content
        
    except Exception as e:
        logger.error(f"Blog generation failed for {youtube_url}: {str(e)}")
        raise RuntimeError(f"Error during blog generation: {str(e)}")
# Original CLI main function
def cli_main():
    """Command line interface for the application"""
    # Get user inputs
    youtube_url = input("Enter YouTube video URL: ").strip()

    try:
        blog_output = generate_blog_from_youtube(youtube_url)
        
        print("\nGenerated blog article:")
        print(blog_output[:200] + "...\n")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cli_main()