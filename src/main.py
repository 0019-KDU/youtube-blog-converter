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

def generate_blog_from_youtube(youtube_url, language='en'):
    """Generate blog article from YouTube video URL"""
    # Input validation
    if not youtube_url or "youtube.com" not in youtube_url:
        raise ValueError("Invalid YouTube URL provided")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
    
    # Set API key in environment
    os.environ["OPENAI_API_KEY"] = api_key

    # Create agents and tasks
    transcriber, writer = create_agents()
    transcript_task, blog_task = create_tasks(transcriber, writer)
    
    # Set up crew
    crew = Crew(
        agents=[transcriber, writer],
        tasks=[transcript_task, blog_task],
        process=Process.sequential
    )

    try:
        logger.info(f"Starting blog generation for: {youtube_url}")
        
        # Execute crew
        crew.kickoff(inputs={
            "youtube_url": youtube_url,
            "language": language
        })
        
        # Handle possible None output
        if not blog_task.output:
            raise RuntimeError("Blog generation failed: no output produced")
            
        blog_output = blog_task.output.raw.strip()
        logger.info(f"Successfully generated blog for: {youtube_url}")
        
    except Exception as e:
        logger.error(f"Blog generation failed for {youtube_url}: {str(e)}")
        raise RuntimeError(f"Error during blog generation: {str(e)}")
    finally:
        # Clean up resources
        del transcriber, writer, transcript_task, blog_task

    return blog_output
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