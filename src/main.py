import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew
from src.agent import create_agents
from src.task import create_tasks

logger = logging.getLogger(__name__)

# Get the path to the .env file in the parent directory
env_path = Path(__file__).resolve().parent.parent / '.env'
logger.info(f"Loading environment from: {env_path}")

# Load environment variables
if env_path.exists():
    logger.info(".env file found, loading environment variables")
    load_dotenv(dotenv_path=env_path)
else:
    logger.warning(".env file not found, falling back to system environment")
    load_dotenv()  # Fallback to default loading

# Debug: Check if OPENAI_API_KEY is loaded
api_key = os.getenv("OPENAI_API_KEY")
logger.info(f"OPENAI_API_KEY loaded: {'Yes' if api_key else 'No'}")

def generate_blog_from_youtube(youtube_url: str, language: str) -> str:
    """Generate a blog article from a YouTube video URL"""
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found")
        raise RuntimeError("OpenAI API key not found")
    
    # Updated input validation to support both youtube.com and youtu.be formats
    if not youtube_url or not ("youtube.com" in youtube_url or "youtu.be" in youtube_url):
        raise ValueError("Invalid YouTube URL provided. Must be a YouTube URL.")
    
    logger.info(f"Starting blog generation for: {youtube_url}")
    
    try:
        # Create agents and tasks
        transcriber, writer = create_agents()
        transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)  # Fixed to pass agents
        
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
        logger.info(f"Successfully generated blog for: {youtube_url}")
        return blog_content
        
    except Exception as e:
        logger.error(f"Blog generation failed for {youtube_url}: {str(e)}")
        raise RuntimeError(f"Error during blog generation: {str(e)}")

def cli_main():
    """Command line interface for the application"""
    # Get user inputs
    youtube_url = input("Enter YouTube video URL: ").strip()
    language = input("Enter language code (e.g., 'en'): ").strip() or "en"

    try:
        blog_output = generate_blog_from_youtube(youtube_url, language)
        
        print("\nGenerated blog article:")
        print(blog_output[:200] + "...\n")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cli_main()